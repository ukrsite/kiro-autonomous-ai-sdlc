"""Unit tests for the FinOps cost model loader."""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

# Load server module from non-standard path
_SERVER_PATH = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "finops-cost-estimator" / "server.py"
_spec = importlib.util.spec_from_file_location("finops_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["finops_server"] = _mod
_spec.loader.exec_module(_mod)


@pytest.fixture()
def valid_model_file(tmp_path):
    """Write a valid cost model YAML and return its path."""
    content = {
        "version": "1.0.0",
        "unit_prices": {
            "llm_tokens_input_per_1k_usd": 0.003,
            "llm_tokens_output_per_1k_usd": 0.015,
            "compute_time_per_second_usd": 0.00005,
            "mcp_tool_invocation_usd": 0.0001,
            "checkpoint_execution_usd": 0.001,
        },
        "defaults": {
            "wf1": {
                "llm_tokens_input": 50000,
                "llm_tokens_output": 20000,
                "compute_time_seconds": 300,
                "mcp_tool_invocations": 40,
                "checkpoint_executions": 4,
            },
            "wf2": {
                "llm_tokens_input": 80000,
                "llm_tokens_output": 30000,
                "compute_time_seconds": 600,
                "mcp_tool_invocations": 60,
                "checkpoint_executions": 3,
                "behavior_equivalence_overhead_usd": 0.05,
            },
            "wf3": {
                "llm_tokens_input": 40000,
                "llm_tokens_output": 15000,
                "compute_time_seconds": 240,
                "mcp_tool_invocations": 50,
                "checkpoint_executions": 4,
            },
            "wf4": {
                "llm_tokens_input": 60000,
                "llm_tokens_output": 25000,
                "compute_time_seconds": 400,
                "mcp_tool_invocations": 45,
                "checkpoint_executions": 5,
            },
            "wf5": {
                "llm_tokens_input": 30000,
                "llm_tokens_output": 20000,
                "compute_time_seconds": 180,
                "mcp_tool_invocations": 20,
                "checkpoint_executions": 2,
            },
        },
        "scaling": {
            "wf1_per_file": {
                "llm_tokens_input": 5000,
                "llm_tokens_output": 2000,
                "compute_time_seconds": 30,
            },
            "wf2_per_file": {
                "llm_tokens_input": 8000,
                "llm_tokens_output": 3000,
                "compute_time_seconds": 60,
            },
            "wf3_per_file": {
                "llm_tokens_input": 3000,
                "llm_tokens_output": 1000,
                "compute_time_seconds": 20,
            },
            "wf4_per_file": {
                "llm_tokens_input": 6000,
                "llm_tokens_output": 2500,
                "compute_time_seconds": 40,
            },
            "wf5_per_file": {
                "llm_tokens_input": 4000,
                "llm_tokens_output": 3000,
                "compute_time_seconds": 25,
            },
        },
    }
    p = tmp_path / "finops-cost-model.yml"
    p.write_text(yaml.dump(content))
    return str(p)


class TestLoadCostModel:
    def test_valid_yaml_loads_and_returns_dict(self, valid_model_file):
        model = _mod._load_cost_model(valid_model_file)
        assert isinstance(model, dict)
        assert model["version"] == "1.0.0"
        assert model["unit_prices"]["llm_tokens_input_per_1k_usd"] == 0.003

    def test_missing_version_raises_descriptive_error(self, tmp_path):
        content = {"unit_prices": {}, "defaults": {"wf1": {}, "wf2": {}}, "scaling": {}}
        p = tmp_path / "model.yml"
        p.write_text(yaml.dump(content))
        with pytest.raises(ValueError, match="version"):
            _mod._load_cost_model(str(p))

    def test_negative_unit_price_raises_descriptive_error(self, tmp_path, valid_model_file):
        import yaml as _yaml
        with open(valid_model_file) as f:
            content = _yaml.safe_load(f)
        content["unit_prices"]["llm_tokens_input_per_1k_usd"] = -0.001
        p = tmp_path / "bad_model.yml"
        p.write_text(_yaml.dump(content))
        with pytest.raises(ValueError, match="llm_tokens_input_per_1k_usd"):
            _mod._load_cost_model(str(p))

    def test_missing_file_raises_error_with_path(self, tmp_path):
        missing = str(tmp_path / "nonexistent.yml")
        with pytest.raises(ValueError, match=str(tmp_path)):
            _mod._load_cost_model(missing)
