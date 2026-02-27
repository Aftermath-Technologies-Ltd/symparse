import pytest
from unittest.mock import patch
import sys
import io
from symparse.cli import main

def test_cli_cache_list_clear(monkeypatch, capsys):
    from symparse.cli import main
    import json
    
    # We can mock CacheManager.list_cache and clear_cache
    class DummyCache:
        def list_cache(self):
            return {"test_schema": "def extract(txt): pass"}
        def clear_cache(self):
            pass
            
    import symparse.cache_manager
    monkeypatch.setattr(symparse.cache_manager, "CacheManager", lambda: DummyCache())
    
    monkeypatch.setattr("sys.argv", ["symparse", "cache", "list"])
    try:
        main()
    except SystemExit:
        pass
        
    out, _ = capsys.readouterr()
    assert "test_schema" in out
    
    monkeypatch.setattr("sys.argv", ["symparse", "-v", "cache", "clear"])
    try:
        main()
    except SystemExit:
        pass
        
    out, _ = capsys.readouterr()
    assert "Cache cleared" in out

def test_cache_list_command(capsys):
    from symparse.cache_manager import CacheManager
    CacheManager().clear_cache()
    
    test_args = ["symparse", "cache", "list"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
    captured = capsys.readouterr()
    assert "{}" in captured.out

def test_run_command_no_stdin(capsys):
    test_args = ["symparse", "run", "--schema", "dummy.json"]
    with patch.object(sys, 'argv', test_args):
        # mock stdin isatty to True
        with patch('sys.stdin.isatty', return_value=True):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Error: No data piped into stdin." in captured.err

def test_run_command_empty_stdin(capsys):
    test_args = ["symparse", "run", "--schema", "dummy.json"]
    with patch.object(sys, 'argv', test_args):
        with patch('sys.stdin.isatty', return_value=False):
            with patch('sys.stdin.read', return_value="   \n  "):
                with pytest.raises(SystemExit) as e:
                    main()
                assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Empty stdin stream." in captured.err

from unittest.mock import mock_open

def test_run_command_success(capsys):
    test_args = ["symparse", "run", "--schema", "dummy.json", "--compile"]
    dummy_schema = '{"type": "object", "properties": {"name": {"type": "string"}}}'
    with patch.object(sys, 'argv', test_args):
        with patch('sys.stdin.isatty', return_value=False):
            with patch('sys.stdin.read', return_value='My name is Alice'):
                with patch('builtins.open', mock_open(read_data=dummy_schema)):
                    with patch('symparse.engine.process_stream', return_value={'name': 'Alice'}):
                        main()
    captured = capsys.readouterr()
    assert '"name": "Alice"' in captured.out
