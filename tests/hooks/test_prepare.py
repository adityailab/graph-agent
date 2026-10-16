from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from handoff.hooks.prepare import MAX_PROMPT_CHARS, prepare_hook_input

HookJson = Callable[[str], dict[str, Any]]
KEY = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz012345"


def test_prepared_prompt_is_redacted_and_capped(hook_json: HookJson) -> None:
    raw = hook_json("user_prompt") | {"prompt": f"use {KEY} " + "x" * 30_000}
    prepared = prepare_hook_input(raw, "/work/app")
    assert KEY not in prepared["prompt"]
    assert len(prepared["prompt"]) == MAX_PROMPT_CHARS


def test_prepared_edit_keeps_only_path_and_redacted_summary(hook_json: HookJson) -> None:
    raw = hook_json("post_edit")
    raw["tool_input"]["new_string"] = f"key = '{KEY}'"
    raw["tool_response"] = {"originalFile": f"old {KEY}"}
    prepared = prepare_hook_input(raw, "/work/app")
    assert prepared["edit_path"] == "hello.txt"
    assert "tool_input" not in prepared
    assert "tool_response" not in prepared
    assert KEY not in json.dumps(prepared)


def test_secret_cut_by_the_summary_cap_is_still_redacted(hook_json: HookJson) -> None:
    body = "\n".join("A" * 64 for _ in range(60))
    pem = f"-----BEGIN RSA PRIVATE KEY-----\n{body}\n-----END RSA PRIVATE KEY-----"
    raw = hook_json("post_write") | {"tool_input": {"file_path": "/work/app/k.pem", "content": pem}}
    assert "A" * 64 not in prepare_hook_input(raw, "/work/app")["edit_summary"]


def test_ids_are_filled_in_when_the_hook_fires(hook_json: HookJson) -> None:
    raw = hook_json("post_edit")
    del raw["prompt_id"], raw["tool_use_id"]
    prepared = prepare_hook_input(raw, "/work/app")
    assert prepared["tool_use_id"]
    prompt = hook_json("user_prompt")
    del prompt["prompt_id"]
    assert prepare_hook_input(prompt, "/work/app")["prompt_id"]


def test_tools_that_do_not_edit_keep_no_tool_details(hook_json: HookJson) -> None:
    raw = hook_json("post_edit") | {"tool_name": "Read", "tool_input": {"file_path": "/x"}}
    prepared = prepare_hook_input(raw, "/work/app")
    assert prepared["edit_path"] is None
    assert prepared["edit_summary"] == ""
