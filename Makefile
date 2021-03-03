# Dummy poc rules
VENV_PATH           := .venv
REQUIREMENTS        := requirements.txt
REQUIREMENTS-BUILD  := requirements-build.txt

.DEFAULT_GOAL := all
.PHONY: all check package venv venv-build doc clean

all: venv

clean:
	rm -rf .eggs/ *.egg-info/ build/ dist/

doc: venv-build
	. "$(VENV_PATH)/bin/activate"   && $(MAKE) -C doc html

check: venv-build
	. "${VENV_PATH}/bin/activate"   && pytest test

package: venv-build check
	rm -rf dist build */*.egg-info *.egg-info
	. "${VENV_PATH}/bin/activate"   && python setup.py sdist bdist_wheel

# Re-using the same .venv ... oh well :/
venv-build: venv-build-init $(REQUIREMENTS-BUILD)

venv-build-init: venv-init

$(REQUIREMENTS-BUILD): venv-build-init
ifneq (,$(wildcard $(REQUIREMENTS-BUILD)))
	. "$(VENV_PATH)/bin/activate"   && pip3 install --quiet -r "$(REQUIREMENTS-BUILD)"
endif

venv: venv-init $(REQUIREMENTS)

venv-init: $(VENV_PATH)
	virtualenv --version >/dev/null || pip3 install --user virtualenv
	test -d "${VENV_PATH}"          || virtualenv --no-site-packages -p python3 "${VENV_PATH}"

$(REQUIREMENTS): venv-init
ifneq (,$(wildcard $(REQUIREMENTS)))
	. "$(VENV_PATH)/bin/activate"   && pip3 install --quiet -r "$(REQUIREMENTS)"
endif

$(VENV_PATH): ;

kodi-addon-check:
	. "${VENV_PATH}/bin/activate"   && kodi-addon-checker --branch matrix | grep -vP '/(.venv|__pycache__|.idea)/'

kodi-package: kodi-addon-check
	git archive HEAD -o "$$(basename "$$(realpath .)")"-0.3.0.zip --prefix="$$(basename "$$(realpath .)")/" ':(exclude,glob)**/.gitignore' ':!.idea' ':!requirements.txt'
