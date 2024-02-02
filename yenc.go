package main

import (
	"errors"
	"strings"
)

func Decode(src []byte) []byte {
	var dst []byte
	var dec byte

	esc := false
	for _, c := range src {
		if c == 13 || c == 10 {
			continue
		}
		if c == 61 && !esc {
			esc = true
			continue
		} else {
			if esc {
				esc = false
				c -= 64
			}
			if c <= 41 {
				dec = c + 214
			} else {
				dec = c - 42
			}
		}
		dst = append(dst, dec)
	}
	return dst
}

func IsData(data []byte) bool {
	return len(data) < 2 || data[0] != '=' || data[1] != 'y'
}

func ParseKeywordLine(s string) (map[string]string, error) {
	words := make(map[string]string)
	for {
		i := strings.LastIndex(s, "=")
		if i == 0 {
			words["type"] = s[2:]
			break
		}
		v := s[i+1:]
		s = s[:i]
		i = strings.LastIndex(s, " ")
		if i < 0 {
      return nil, errors.New("invalid keyword line")
		}
		k := s[i+1:]
		s = s[:i]
		words[k] = v
	}
	if len(words) == 0 {
		return nil, errors.New("invalid keyword line")
	}
	return words, nil
}
