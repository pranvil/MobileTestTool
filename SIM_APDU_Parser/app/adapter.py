
from typing import List, Dict, Optional
from SIM_APDU_Parser.pipeline import Pipeline
from SIM_APDU_Parser.render.tree_builder import to_tree_for_gui

class GuiSession:
    def __init__(self, path: str, prefer_mtk: bool = True, show_normal: bool = False, use_qualcomm: bool = False):
        self.path = path
        self.prefer_mtk = prefer_mtk
        self.use_qualcomm = use_qualcomm
        self._pipeline = Pipeline(prefer_mtk=prefer_mtk, show_normal_sim=True, use_qualcomm=use_qualcomm)  # parse all; filter later
        self._results = self._pipeline.run_from_file(path)  # keep full results
        self._show_normal = show_normal
        self._allowed_types: list[str] = []
        self._events = self._rebuild_events()

    def _rebuild_events(self) -> List[Dict]:
        from SIM_APDU_Parser.render.gui_adapter import to_gui_events
        return to_gui_events(self._results, show_normal_sim=self._show_normal, allowed_types=self._allowed_types)

    @property
    def events(self) -> List[Dict]:
        return self._events

    def set_show_normal(self, flag: bool):
        self._show_normal = flag
        self._events = self._rebuild_events()

    def set_allowed_types(self, kinds: list[str]):
        self._allowed_types = kinds[:]
        self._events = self._rebuild_events()

    # Detail by raw hex (for minimal GUI change)
    def get_tree_by_raw(self, raw: str) -> Dict:
        raw = (raw or "").replace(" ", "").upper()
        for r in self._results:
            if r.message.raw == raw:
                return to_tree_for_gui(r)
        return {"text":"(not found)","children":[]}

# convenience function
def load_for_gui(path: str, prefer_mtk: bool = True, show_normal: bool = False, use_qualcomm: bool = False) -> GuiSession:
    return GuiSession(path, prefer_mtk=prefer_mtk, show_normal=show_normal, use_qualcomm=use_qualcomm)
