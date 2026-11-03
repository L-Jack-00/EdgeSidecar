import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import RULES_FILE

DEFAULT_RULES = [
    {
        "id": "cors-unblocker",
        "name": "전역 CORS 제한 해제 (Bypass CORS Everywhere)",
        "enabled": True,
        "url_pattern": ".*",
        "action": "modify_response",
        "add_response_headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true"
        },
        "remove_response_headers": [
            "content-security-policy",
            "x-frame-options"
        ]
    },
    {
        "id": "custom-header-injection",
        "name": "커스텀 헤더 주입 예시 (Custom Header Injection)",
        "enabled": False,
        "url_pattern": ".*",
        "action": "modify_request",
        "add_request_headers": {
            "X-Sidecar-Agent": "EdgeSidecar-v1.0"
        }
    },
    {
        "id": "mock-api-demo",
        "name": "특정 API 모킹 예시 (Mock API Demo)",
        "enabled": False,
        "url_pattern": "https://api\\.example\\.com/user",
        "action": "mock_response",
        "mock_status": 200,
        "mock_content_type": "application/json; charset=utf-8",
        "mock_body": '{"status": "success", "user": "EdgeSidecar Master", "role": "Root"}'
    }
]

class RuleEngine:
    def __init__(self, rules_path: Path = RULES_FILE):
        self.rules_path = rules_path
        self.rules: List[Dict[str, Any]] = []
        self.load_rules()

    def load_rules(self):
        if self.rules_path.exists():
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    self.rules = json.load(f)
                return
            except Exception as e:
                print(f"[RuleEngine] Error loading rules: {e}")
        self.rules = DEFAULT_RULES
        self.save_rules()

    def save_rules(self):
        with open(self.rules_path, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, indent=2, ensure_ascii=False)

    def get_rules(self) -> List[Dict[str, Any]]:
        return self.rules

    def set_rules(self, rules: List[Dict[str, Any]]):
        self.rules = rules
        self.save_rules()

    def toggle_rule(self, rule_id: str) -> bool:
        for r in self.rules:
            if r.get("id") == rule_id:
                r["enabled"] = not r.get("enabled", True)
                self.save_rules()
                return r["enabled"]
        return False

    def add_rule(self, rule: Dict[str, Any]):
        self.rules.append(rule)
        self.save_rules()

    def delete_rule(self, rule_id: str):
        self.rules = [r for r in self.rules if r.get("id") != rule_id]
        self.save_rules()

    def match_request_rules(self, url: str) -> List[Dict[str, Any]]:
        matched = []
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            pattern = rule.get("url_pattern", "")
            try:
                if re.search(pattern, url, re.IGNORECASE):
                    matched.append(rule)
            except re.error:
                continue
        return matched
