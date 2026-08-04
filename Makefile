.PHONY: help install install-dev install-minimal test test-fast test-coverage lint format format-check build clean clean-all

help install install-dev install-minimal test test-fast test-coverage lint format format-check build clean clean-all:
	$(MAKE) -C opencellcomms_engine $@
