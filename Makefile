DOCKER_IMAGE  := go60-zmk-config-docker
DOCKER_VOLUME := go60-zmk-nix-store
KEYMAP_WORD_RE := &?[A-Za-z_][A-Za-z_0-9]*(\([^)]*\))?

.PHONY: help build build-fast build-rebuild flash flash-slow draw ident ident-html layers diff diff-keymap setup-git clean nuke

help:
	@echo "Targets:"
	@echo "  build          Build firmware via Docker (./build.sh)."
	@echo "  build-fast     Build, skipping the in-container 'git fetch origin'."
	@echo "  build-rebuild  Force a fresh 'docker build' before building."
	@echo "  flash          Build (skipping fetch), then copy go60.uf2 onto the bootloader drive."
	@echo "  flash-slow     Same as flash but does the in-container 'git fetch origin' first."
	@echo "  draw           Render keymap-drawer/keymap.svg from config/go60.keymap."
	@echo "  ident          Run the terminal key-position identifier."
	@echo "  ident-html     Open the browser-based key-position identifier."
	@echo "  layers         Open the layer popup viewer (builds binary if needed)."
	@echo "  diff           Token-aware word-diff for the keymap (vs. HEAD)."
	@echo "  diff-keymap    Same as diff. REF=<rev> compares against another ref."
	@echo "  setup-git      Install a token-aware diff driver for *.keymap files."
	@echo "  clean          Remove generated outputs (keymap-drawer/, combined symlink)."
	@echo "  nuke           Drop the Docker image and Nix-store volume (full reset)."
	@echo ""
	@echo "Variables: BRANCH=<ref> picks a ZMK ref. Example: make build BRANCH=v0.2-rc1"

build:
	./build.sh $(BRANCH)

build-fast:
	SKIP_FETCH=1 ./build.sh $(BRANCH)

build-rebuild:
	REBUILD=1 ./build.sh $(BRANCH)

flash:
	SKIP_FETCH=1 ./flash.sh $(BRANCH)

flash-slow:
	./flash.sh $(BRANCH)

draw:
	./draw.sh

ident:
	python3 tools/key-id.py

ident-html:
	open tools/key-id.html

layers: tools/layer-popup
	U_KBD_KEYMAP=$(CURDIR)/keymap-drawer/layers tools/layer-popup

tools/layer-popup: tools/layer-popup.swift
	swiftc tools/layer-popup.swift -o tools/layer-popup

# Word-aware diff for *.keymap. Treat each ZMK token as one "word" so a
# single-key edit shows as a one-token swap rather than a 600-char line.
diff diff-keymap:
	@git diff --color-words='$(KEYMAP_WORD_RE)' $(if $(REF),$(REF) --,) -- config/go60.keymap

# One-time: register a diff driver so plain `git diff` / `git log -p` use the
# same word regex on *.keymap files (the .gitattributes line `diff=keymap`
# activates only after this driver is installed).
setup-git:
	git config diff.keymap.wordRegex '$(KEYMAP_WORD_RE)'
	@echo "OK — *.keymap diffs now use the token-aware word regex."

clean:
	rm -rf keymap-drawer combined

nuke:
	-docker image rm $(DOCKER_IMAGE)
	-docker volume rm $(DOCKER_VOLUME)
