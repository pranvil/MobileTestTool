"""
创建Test Progress业务逻辑
包含两层校验：文件级校验和行级校验
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from Jira_tool.jira_client import get_fields, create_issue
from Jira_tool.core.paths import get_progress_logs_path, get_error_reports_path
from core.debug_logger import logger
from Jira_tool.core.exceptions import ValidationError, JiraAPIError, FileError

# 必需列
REQUIRED_COLUMNS = ['Project', 'Summary', 'StartDate', 'FinishDate']
ISSUE_TYPE = 'Test Progress'


def validate_file_structure(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    文件级校验：检查必需列是否存在
    
    Args:
        df: DataFrame
    
    Returns:
        (is_valid, missing_columns)
        - is_valid: 是否通过校验
        - missing_columns: 缺失的列名列表
    """
    logger.debug("开始文件级校验")
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    
    if missing_columns:
        logger.warning(f"文件级校验失败，缺失列: {missing_columns}")
        return False, missing_columns
    
    logger.info("文件级校验通过")
    return True, []


def validate_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    行级校验：逐行检查数据合法性
    
    Args:
        df: DataFrame
    
    Returns:
        errors列表，每个元素包含 {row_index, row_number, error_message, row_data}
    """
    logger.debug("开始行级校验")
    errors = []
    
    for index, row in df.iterrows():
        row_number = index + 2  # Excel行号（从2开始，因为第1行是表头）
        row_errors = []
        
        # 检查Project
        project = row.get('Project', '')
        if pd.isna(project) or str(project).strip() == '':
            row_errors.append("Project字段为空")
        else:
            # 去除多余空格
            project_clean = str(project).strip()
            if project_clean != str(project):
                logger.warning(f"第{row_number}行：Project包含多余空格，已自动去除")
        
        # 检查Summary
        summary = row.get('Summary', '')
        if pd.isna(summary) or str(summary).strip() == '':
            row_errors.append("Summary字段为空")
        
        # 检查StartDate
        start_date = row.get('StartDate')
        start_date_valid = False
        if pd.isna(start_date):
            row_errors.append("StartDate字段为空")
        else:
            try:
                start_date = pd.to_datetime(start_date)
                start_date_valid = True
            except:
                row_errors.append("StartDate格式错误（应为日期格式）")
        
        # 检查FinishDate
        finish_date = row.get('FinishDate')
        finish_date_valid = False
        if pd.isna(finish_date):
            row_errors.append("FinishDate字段为空")
        else:
            try:
                finish_date = pd.to_datetime(finish_date)
                finish_date_valid = True
            except:
                row_errors.append("FinishDate格式错误（应为日期格式）")
        
        # 检查日期逻辑
        if start_date_valid and finish_date_valid:
            if start_date > finish_date:
                row_errors.append("StartDate不能晚于FinishDate")
        
        # 如果有错误，添加到错误列表
        if row_errors:
            errors.append({
                'row_index': index,
                'row_number': row_number,
                'error_message': '; '.join(row_errors),
                'row_data': row.to_dict()
            })
            logger.warning(f"第{row_number}行校验失败: {'; '.join(row_errors)}")
    
    logger.info(f"行级校验完成，发现 {len(errors)} 个错误")
    return errors


def format_date_for_jira(date_obj) -> Optional[str]:
    """
    将日期转换为JIRA需要的格式
    
    Args:
        date_obj: 日期对象（可以是datetime、字符串等）
    
    Returns:
        YYYY-MM-DD格式的字符串，如果转换失败返回None
    """
    if pd.isna(date_obj):
        return None
    
    try:
        if isinstance(date_obj, str):
            date_obj = pd.to_datetime(date_obj)
        return date_obj.strftime('%Y-%m-%d')
    except:
        return None


def build_issue_payload(row: pd.Series, project_key: str, fields_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据行数据和字段定义构建创建Issue的payload
    
    Args:
        row: DataFrame的一行
        project_key: 项目Key
        fields_def: 字段定义字典（字段ID -> 字段信息）
    
    Returns:
        JIRA API格式的payload
    """
    payload = {
        "fields": {
            "project": {
                "key": project_key
            },
            "issuetype": {
                "name": ISSUE_TYPE
            },
            "summary": str(row['Summary']).strip()
        }
    }
    
    # 处理日期字段
    start_date = format_date_for_jira(row.get('StartDate'))
    finish_date = format_date_for_jira(row.get('FinishDate'))
    
    # 从字段定义中查找日期字段
    start_field_id = None
    finish_field_id = None
    
    for field_id, field_info in fields_def.items():
        field_name = field_info.get('name', '')
        # 查找Plan Start Date字段
        if not start_field_id and ('Plan Start Date' in field_name or 
                                   ('Start' in field_name and 'Date' in field_name)):
            start_field_id = field_id
        # 查找Plan Finish Date字段
        if not finish_field_id and ('Plan Finish Date' in field_name or 
                                    ('Finish' in field_name and 'Date' in field_name)):
            finish_field_id = field_id
    
    # 设置日期字段
    if start_date:
        if start_field_id:
            payload['fields'][start_field_id] = start_date
        else:
            # 如果没找到，使用已知的字段ID（向后兼容）
            payload['fields']['customfield_21686'] = start_date
            logger.warning(f"未找到Start Date字段定义，使用默认字段ID: customfield_21686")
    
    if finish_date:
        if finish_field_id:
            payload['fields'][finish_field_id] = finish_date
        else:
            # 如果没找到，使用已知的字段ID（向后兼容）
            payload['fields']['customfield_21687'] = finish_date
            logger.warning(f"未找到Finish Date字段定义，使用默认字段ID: customfield_21687")
    
    # 处理 Amount - Function 字段（可选）
    amount_function_field_id = None
    for field_id, field_info in fields_def.items():
        field_name = field_info.get('name', '')
        if 'Amount - Function' in field_name or (field_name == 'Amount - Function'):
            amount_function_field_id = field_id
            break
    
    # 如果 Excel 中有 Amount - Function 列，则设置该字段
    if 'Amount - Function' in row.index:
        amount_function_value = row.get('Amount - Function')
        if not pd.isna(amount_function_value) and str(amount_function_value).strip() != '':
            try:
                # 转换为数字
                amount_function_num = float(amount_function_value)
                if amount_function_field_id:
                    payload['fields'][amount_function_field_id] = amount_function_num
                else:
                    # 如果没找到，使用已知的字段ID（向后兼容）
                    payload['fields']['customfield_14036'] = amount_function_num
                    logger.warning(f"未找到Amount - Function字段定义，使用默认字段ID: customfield_14036")
            except (ValueError, TypeError) as e:
                logger.warning(f"Amount - Function字段值转换失败: {amount_function_value}, 错误: {e}")
    
    return payload


def create_issues_from_excel(
    excel_path: str,
    skip_errors: bool = True
) -> Dict[str, Any]:
    """
    从Excel文件批量创建Issue
    
    Args:
        excel_path: Excel文件路径
        skip_errors: 是否跳过错误行继续创建
    
    Returns:
        包含创建结果的字典
    """
    logger.info(f"开始批量创建Issue，文件: {excel_path}, skip_errors={skip_errors}")
    
    try:
        # 读取Excel
        df = pd.read_excel(excel_path)
        logger.info(f"读取Excel成功，共 {len(df)} 行")
        
        # 文件级校验
        is_valid, missing_columns = validate_file_structure(df)
        if not is_valid:
            error_msg = f"文件级校验失败，缺失列: {missing_columns}"
            logger.error(error_msg)
            raise ValidationError(error_msg, errors=[{'type': 'file', 'message': error_msg}])
        
        # 行级校验
        validation_errors = validate_rows(df)
        
        # 如果选择不跳过错误，且有校验错误，直接返回
        if not skip_errors and validation_errors:
            error_msg = f"行级校验失败，发现 {len(validation_errors)} 个错误"
            logger.error(error_msg)
            raise ValidationError(error_msg, errors=validation_errors)
        
        # 过滤掉有错误的行（如果选择跳过错误）
        if skip_errors and validation_errors:
            error_row_indices = {err['row_index'] for err in validation_errors}
            df_valid = df[~df.index.isin(error_row_indices)]
            logger.info(f"跳过 {len(error_row_indices)} 个错误行，剩余 {len(df_valid)} 行")
        else:
            df_valid = df
        
        # 批量创建
        results = []
        success_count = 0
        fail_count = 0
        
        for index, row in df_valid.iterrows():
            try:
                project_key = str(row['Project']).strip()
                
                # 获取字段定义
                try:
                    fields_def = get_fields(project_key, ISSUE_TYPE)
                    logger.debug(f"获取到 {len(fields_def)} 个字段定义")
                except Exception as e:
                    logger.warning(f"获取字段定义失败，使用默认字段ID: {e}")
                    fields_def = {}
                
                # 构建payload
                payload = build_issue_payload(row, project_key, fields_def)
                
                # 创建Issue
                result = create_issue(payload)
                issue_key = result.get('key', '')
                
                results.append({
                    'row_index': index,
                    'status': 'Success',
                    'issue_key': issue_key,
                    'error_message': None
                })
                success_count += 1
                logger.info(f"创建成功: {issue_key} - {row['Summary']}")
            
            except Exception as e:
                error_msg = str(e)
                results.append({
                    'row_index': index,
                    'status': 'Failed',
                    'issue_key': None,
                    'error_message': error_msg
                })
                fail_count += 1
                logger.error(f"创建失败 (第{index+2}行): {error_msg}")
        
        # 保存创建进度日志
        log_content = f"""
批量创建Issue日志
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
文件: {excel_path}
总数: {len(df)}
成功: {success_count}
失败: {fail_count}
跳过错误行: {skip_errors}

详细结果:
"""
        for result in results:
            log_content += f"\n行{result['row_index']+2}: {result['status']}"
            if result['issue_key']:
                log_content += f" - {result['issue_key']}"
            if result['error_message']:
                log_content += f" - {result['error_message']}"
        
        log_dir = get_progress_logs_path()
        log_filename = f"create_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = log_dir / log_filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        logger.info(f"创建进度日志已保存: {log_path}")
        
        # 如果有失败的行，导出错误报告
        failed_results = [r for r in results if r['status'] == 'Failed']
        if failed_results or validation_errors:
            export_error_report(df, failed_results, validation_errors)
        
        return {
            'success': True,
            'total': len(df),
            'success_count': success_count,
            'fail_count': fail_count,
            'validation_errors': validation_errors,
            'results': results,
            'log_path': str(log_path)
        }
    
    except ValidationError:
        raise
    except Exception as e:
        error_msg = f"批量创建失败: {e}"
        logger.exception(error_msg)
        raise FileError(error_msg)


def export_error_report(
    df: pd.DataFrame,
    failed_results: List[Dict[str, Any]],
    validation_errors: List[Dict[str, Any]]
):
    """
    导出错误报告到Excel
    
    Args:
        df: 原始DataFrame
        failed_results: 创建失败的结果列表
        validation_errors: 校验错误列表
    """
    logger.info("开始导出错误报告")
    
    try:
        error_dir = get_error_reports_path()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"error_report_{timestamp}.xlsx"
        file_path = error_dir / filename
        
        # 收集所有错误行
        error_rows = []
        
        # 添加校验错误
        for err in validation_errors:
            row_data = err['row_data'].copy()
            row_data['错误原因'] = f"校验错误: {err['error_message']}"
            error_rows.append(row_data)
        
        # 添加创建失败的行
        for result in failed_results:
            row_index = result['row_index']
            if row_index < len(df):
                row_data = df.iloc[row_index].to_dict()
                row_data['错误原因'] = f"创建失败: {result['error_message']}"
                error_rows.append(row_data)
        
        if error_rows:
            error_df = pd.DataFrame(error_rows)
            error_df.to_excel(file_path, index=False, engine='openpyxl')
            logger.info(f"错误报告已导出: {file_path}")
        else:
            logger.warning("没有错误行需要导出")
    
    except Exception as e:
        logger.exception(f"导出错误报告失败: {e}")

