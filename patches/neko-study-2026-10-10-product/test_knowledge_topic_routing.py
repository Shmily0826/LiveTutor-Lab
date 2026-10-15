"""Offline regression for subject-correct but topic-unrelated graph guidance."""
import ast
import asyncio
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LIVE = ROOT / "benchmarks/raw/neko-product-data/plugin-code/study_companion"
PAYLOAD = Path(__file__).with_name("payload") / "study_companion"
# The result JSON carries Chinese topic names; on a default Windows console
# (cp1252) that makes the final print alone fail the test.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
package = ModuleType("routing_test")
package.__path__ = [str(PAYLOAD), str(LIVE)]
sys.modules[package.__name__] = package
graph = importlib.import_module("routing_test.knowledge_graph_guidance")
Semantics = importlib.import_module("routing_test._semantic_routing").StudyInputSemantics
topics = json.loads((LIVE / "static/knowledge_seeds/computer_science.json").read_text(encoding="utf-8"))["topics"]
transcript = json.loads((ROOT / "benchmarks/raw/evidence/flutter-product-transcript.json").read_text(encoding="utf-8-sig"))
round5 = next(item for item in transcript if item.get("round") == 5)
assert "Focus topic: 拓扑排序" in round5["tutor"], "Original visible defect evidence missing"

tree = ast.parse((PAYLOAD / "entry_tutor_context_support.py").read_text(encoding="utf-8"))
outcome = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_knowledge_guidance_outcome")
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "_TutorContextSupportMixin")
method = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "_build_knowledge_guidance_context")
namespace = {"Any": Any, "asyncio": asyncio, "StudyInputSemantics": Semantics,
             "match_topics": graph.match_topics, "build_knowledge_guidance_payload": graph.build_knowledge_guidance_payload,
             "LLM_OPERATION_CONCEPT_EXPLAIN": "explain", "LLM_OPERATION_KNOWLEDGE_TRACK": "track",
             "LLM_OPERATION_SUMMARIZE_SESSION": "summary", "_SEMANTIC_ROUTE_MIN_CONFIDENCE": 0.6,
             "phase": lambda name: __import__("contextlib").nullcontext()}
exec(compile(ast.fix_missing_locations(ast.Module(body=[outcome, method], type_ignores=[])), "patched_context_support", "exec"), namespace)


def classification(entity, concepts):
    return Semantics(subject="computer_science", content_type="concept explanation",
                     intent="check correctness and boundary conditions", response_mode="general_explanation",
                     entity=entity, retrieval_concepts=tuple(concepts), confidence=0.95)


host = SimpleNamespace(_knowledge_guidance_topics_cache={"all:5000": topics})


async def route(semantics, selected=""):
    async def classified(*args, **kwargs):
        return semantics, "available", ""
    host._route_study_input_semantics = classified
    return await namespace["_build_knowledge_guidance_context"](
        host, operation="explain", input_text=round5["student"], context={"selected_topic_id": selected})


async def check():
    # Stress the actual defect mechanism with generic same-subject terms. These
    # classifications are offline inputs, not claims about the hidden model JSON.
    generic = classification("Flutter Provider context.watch context.read",
                             ["状态更新", "依赖关系", "变量状态", "边界条件", "输入输出"])
    ranking = graph.match_topics(topics, query=" ".join((generic.entity, *generic.retrieval_concepts)),
                                 subject="computer_science")
    assert ranking and ranking[0]["score"] >= 10, ranking
    assert all(item["topic_specific_score"] < 10 for item in ranking), ranking
    guidance, result = await route(generic)
    assert not guidance and result["knowledge_guidance_status"] == "not_matched", result
    assert not result["knowledge_guidance_related_topics"]
    confirmed = []
    for topic in topics:
        if "拓扑排序" not in topic["name"] and "BFS" not in topic["name"]:
            continue
        guidance, result = await route(classification(topic["name"], [topic["name"]]))
        assert result["knowledge_guidance_status"] == "applied", result
        assert result["knowledge_guidance_focus_topic"]["id"] == topic["id"], result
        confirmed.append(topic["name"])
    assert any("BFS" in name for name in confirmed) and "拓扑排序" in confirmed, confirmed
    guidance, result = await route(classification("BFS", ["BFS"]))
    assert result["knowledge_guidance_status"] == "applied" and "BFS" in result["knowledge_guidance_focus_topic"]["label"], result
    alias_topics = [{"id": "synthetic_http", "name": "HTTP 缓存", "subject": "computer_science", "aliases": ["HTTP caching"]}]
    aliases = graph.match_topics(alias_topics, query="HTTP caching", subject="computer_science")
    assert aliases and aliases[0]["topic_specific_score"] >= 10
    selected = next(topic for topic in topics if topic["name"] == "拓扑排序")
    guidance, result = await route(generic, selected["id"])
    assert result["knowledge_guidance_status"] == "applied" and result["knowledge_guidance_source"] == "selected_topic"
    # Scene41's real question must not become a grammar lesson in non-explain paths.
    all_topics = []
    for path in sorted((LIVE / 'static/knowledge_seeds').glob('*.json')):
        all_topics.extend(json.loads(path.read_text(encoding='utf-8')).get('topics', []))
    arrow_query = '已有关系对照图的两条连接是 WEX→NUD、NUD→REZ。从 NUD 出发的那条箭头，起点和终点分别是什么？'
    async def automatic(operation, query, selected_id=''):
        fixture = SimpleNamespace(_knowledge_guidance_topics_cache={'all:5000':all_topics})
        return await namespace['_build_knowledge_guidance_context'](
            fixture, operation=operation, input_text=query,
            context={'selected_topic_id':selected_id})
    assert '从' not in graph._query_terms(arrow_query)
    assert all(item.get('topic_specific_score',0) < 10 for item in graph.match_topics(all_topics, query=arrow_query))
    for operation in ('answer', 'question'):
        for query in (arrow_query, '连接', '从', 'input output boundary conditions'):
            guidance, result = await automatic(operation, query)
            assert not guidance and result['knowledge_guidance_status']=='not_matched', (operation, query, result)
        for query in ('从句连接词选择', '图的 BFS 与 DFS', 'BFS'):
            guidance, result = await automatic(operation, query)
            assert result['knowledge_guidance_status']=='applied', (query, result)
            assert guidance['topic']['id']==guidance['relevant_subgraph']['focus_topics'][0]['id']
        guidance, result = await automatic(operation, arrow_query, 'english_senior_clause_connection')
        assert result['knowledge_guidance_source']=='selected_topic' and guidance['topic']['subject']=='english'
    # Complete aliases/identifiers work; a longer source identifier is not that alias.
    identifier_topics=[{'id':'named_bfs','name':'Breadth-first traversal','subject':'computer_science','aliases':['BFS']}]
    assert graph.match_topics(identifier_topics,query='Use BFS.') [0]['topic_specific_score'] >= 10
    assert not any(item['topic_specific_score']>=10 for item in graph.match_topics(identifier_topics,query='BFSx'))
    single_character=[{'id':'force','name':'力','subject':'physics'}]
    assert graph.match_topics(single_character,query='力')[0]['topic_specific_score']>=10
    assert not graph.match_topics(single_character,query='能力培养')
    return {"status": "PASS_TOPIC_SPECIFIC_KNOWLEDGE_ROUTING", "original_evidence_round": 5,
            "generic_overlap_rejected": True, "name_matches_preserved": confirmed,
            "bfs_keyword_preserved": True, "aliases_preserved": True,
            "explicit_topic_preserved": True, "non_explain_generic_overlap_rejected": True,
            "cross_subject_seeds_checked": len(all_topics), "source_identifier_boundary_preserved": True,
            "provider_calls": 0, "live_ui_retested": False}


print(json.dumps(asyncio.run(check()), ensure_ascii=False, indent=2))
