"""Convenience launcher from repo root:  python run_competitions.py [--demo]"""
import runpy
import sys

sys.argv[0] = "competitions.main"
runpy.run_module("competitions.main", run_name="__main__")
