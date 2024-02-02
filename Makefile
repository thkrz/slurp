GO ?= go
GOFLAGS :=
BUILD_OPTS ?= -trimpath
GO_LDFLAGS := -s -w

all: slurp

slurp:
	$(GO) build $(BUILD_OPTS) $(GOFLAGS) -ldflags "$(GO_LDFLAGS)" -o $@

man: doc/slurp.1.scd
	scdoc < $< > slurp.1

clean:
	rm -f slurp slurp.1

.PHONEY: all clean
