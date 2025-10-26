
from typing import List
from SIM_APDU_Parser.core.models import ParseResult, MsgType, Message
from SIM_APDU_Parser.data_io.loaders import load_text
from SIM_APDU_Parser.data_io.extractors.mtk import MTKExtractor
from SIM_APDU_Parser.data_io.extractors.generic import GenericExtractor
from SIM_APDU_Parser.data_io.extractors.qualcomm import QualcommExtractor
from SIM_APDU_Parser.classify.rules import classify_message
from SIM_APDU_Parser.parsers.base import CatParser, EsimParser, NormalSimParser
from SIM_APDU_Parser.render.gui_adapter import to_gui_events

class Pipeline:
    def __init__(self, prefer_mtk: bool = True, show_normal_sim: bool = False, use_qualcomm: bool = False):
        self.extractor_mtk = MTKExtractor()
        self.extractor_generic = GenericExtractor()
        self.extractor_qualcomm = QualcommExtractor()
        self.prefer_mtk = prefer_mtk
        self.show_normal_sim = show_normal_sim
        self.use_qualcomm = use_qualcomm

    def run_from_file(self, path: str) -> List[ParseResult]:
        print(f"[DEBUG] Pipeline.run_from_file() called with path: {path}")
        print(f"[DEBUG] Pipeline settings: prefer_mtk={self.prefer_mtk}, use_qualcomm={self.use_qualcomm}")
        
        print("[DEBUG] Loading text from file...")
        text = load_text(path)
        print(f"[DEBUG] Text loaded, length: {len(text)} characters")
        
        print("[DEBUG] Extracting messages...")
        if self.use_qualcomm:
            print("[DEBUG] Using Qualcomm extractor")
            messages = self.extractor_qualcomm.extract_from_text(text)
        elif self.prefer_mtk:
            print("[DEBUG] Using MTK extractor")
            messages = self.extractor_mtk.extract_from_text(text)
        else:
            print("[DEBUG] Using Generic extractor")
            messages = self.extractor_generic.extract(text.splitlines())
        
        print(f"[DEBUG] Extracted {len(messages)} messages")
        print("[DEBUG] Running message parsing...")
        results = self._run_messages(messages)
        print(f"[DEBUG] Parsing completed, {len(results)} results")
        return results

    def _run_messages(self, messages: List[Message]) -> List[ParseResult]:
        print(f"[DEBUG] Pipeline._run_messages() called with {len(messages)} messages")
        results: List[ParseResult] = []
        for i, m in enumerate(messages):
            if i < 5:  # 只对前5个消息显示详细debug
                print(f"[DEBUG] Processing message {i+1}: {m.raw[:50]}...")
            
            msg_type, direction, tag, title = classify_message(m)
            if i < 5:
                print(f"[DEBUG] Message {i+1} classified as: {msg_type}, direction: {direction}")
            
            if msg_type == MsgType.CAT:
                parser = CatParser()
            elif msg_type == MsgType.ESIM:
                parser = EsimParser()
            elif msg_type == MsgType.NORMAL_SIM:
                parser = NormalSimParser()
            else:
                parser = NormalSimParser()
            
            if i < 5:
                print(f"[DEBUG] Message {i+1} using parser: {type(parser).__name__}")
            
            pr = parser.parse(m)
            # For CAT messages, keep the detailed title from the parser
            # For other message types, use the title from classify_message
            if msg_type != MsgType.CAT:
                pr.title = title
            pr.direction_hint = direction
            pr.tag = tag
            results.append(pr)
        
        print(f"[DEBUG] _run_messages completed, {len(results)} results")
        return results
