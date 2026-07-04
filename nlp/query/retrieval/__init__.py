"""Retrieval package for hybrid search (graph + vector) and analytics.

Submodules are imported directly by callers (e.g. `from nlp.query.retrieval.analytics
import dashboard_summary`) rather than re-exported here, so that importing one submodule
doesn't pull in the others' dependencies (e.g. torch, only needed by reranking).
"""
