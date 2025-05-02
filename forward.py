# forward.py
# auther: https://github.com/Hanschase
import json
import re
import aiohttp
import os
from typing import List, Dict

class ForwardMessage:
    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"
    
    async def send_forward(
        self,
        launcher_id: str,
        messages: List[Dict],
        prompt: str = "默认提示",
        summary: str = "默认摘要",
        source: str = "默认来源",
        user_id: str = "100000",
        nickname: str = "消息助手",
        mode: str = "single"  # 新增模式参数
    ) -> dict:
        """发送合并转发消息"""
        # 构建消息节点
        if mode == "single":
            nodes = self._build_single_node(messages, user_id, nickname)
            item_count = len(nodes[0]['data']['content']) if nodes else 0
        else:
            nodes = self._build_nodes(messages, user_id, nickname)
            item_count = len(nodes)
        
        # 自动追加统计信息
        formatted_summary = f"{summary} | 共{item_count}条内容"
        
        message_data = {
            "group_id": launcher_id,
            "messages": nodes,
            "prompt": prompt,
            "summary": formatted_summary,
            "source": source
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/send_forward_msg",
                json=message_data,
                headers={'Content-Type': 'application/json'}
            ) as resp:
                return await resp.json()

    def _build_single_node(self, messages: List[Dict], user_id: str, nickname: str) -> List[Dict]:
        """构建单节点消息"""
        return [{
            "type": "node",
            "data": {
                "user_id": user_id,
                "nickname": nickname,
                "content": self._parse_contents(messages)
            }
        }]
    
    def _build_nodes(self, messages: List[Dict],user_id: str, nickname: str) -> List[Dict]:
        """构建消息节点"""
        nodes = []
        for idx, msg in enumerate(messages):
            node = {
                "type": "node",
                "data": {
                    "user_id": user_id,
                    "nickname": nickname,
                    "content": self._parse_content(msg)
                }
            }
            nodes.append(node)
        return nodes

    def _parse_contents(self, messages: Dict) -> List[Dict]:
        """解析全部消息内容"""
        contents = []
        for msg in messages:
            contents.extend(self._parse_content(msg))  # 使用_parse_content来处理每条消息
        return contents
    
    def _parse_content(self, msg: Dict) -> List[Dict]:
        """解析消息内容"""
        # content = []
        # if 'image' in msg:
        #     content.append({
        #         "type": "image",
        #         "data": {"file": self._get_media_path(msg['image'])}
        #     })
        # if 'text' in msg:
        #     content.append({
        #         "type": "text",
        #         "data": {"text": msg['text']}
        #     })
        return msg.get("content", [])

        # return content

    def _get_media_path(self, path: str) -> str:
        """获取合法媒体路径"""
        if path.startswith(('http://', 'https://')):
            return path
        if os.path.isfile(path):
            return f"file:///{os.path.abspath(path)}"
        return ""
    
    def convert_to_forward(self, raw_message: str) -> list[dict]:
        """升级版消息解析，按块分组，保留图文顺序"""
        messages = []

        for block in raw_message.split('\n---\n'):
            block = block.strip()
            if not block:
                continue
            content = []
            elements = re.split(r'(!\[.*?\]\(.*?\))', block)
            for elem in elements:
                elem = elem.strip()
                if not elem:
                    continue
                if elem.startswith('!['):  # 图片
                    match = re.match(r'!\[.*?\]\((.*?)\)', elem)
                    if match:
                        content.append({
                            "type": "image",
                            "data": {"file": match.group(1)}
                        })
                else:  # 文本
                    content.append({
                        "type": "text",
                        "data": {"text": elem}
                    })
            if content:
                messages.append({"content": content})
        return messages
