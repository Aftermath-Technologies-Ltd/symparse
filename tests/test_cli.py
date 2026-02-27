import pytest
from unittest.mock import patch
import sys
import io
from symparse.cli import main

def test_cache_list_command(capsys):
    test_args = ["symparse", "cache", "list"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
    captured = capsys.readouterr()
    assert "TODO: cache list" in captured.out

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

def test_run_command_success(capsys):
    test_args = ["symparse", "run", "--schema", "dummy.json", "--compile"]
    with patch.object(sys, 'argv', test_args):
        with patch('sys.stdin.isatty', return_value=False):
            with patch('sys.stdin.read', return_value="valid data"):
                main() # Should not raise SystemExit
    captured = capsys.readouterr()
    assert "Schema: dummy.json, Compile: True, Force AI: False" in captured.out
    assert "Input: valid data..." in captured.out
