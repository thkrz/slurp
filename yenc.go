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

func Params(s string) (map[string]string, error) {
  i := strings.Index(s, " ")
  if i < 0 {
    return nil, errors.New("invalid keyword line")
  }
  p := make(map[string]string)
  p["type"] = s[2:i]
  q := strings.Split(s[i+1:], "=")
  for i = 0; i < len(q)-1; i++ {
    k := strings.TrimSpace(q[i])
    v := strings.TrimSpace(q[i+1])
    p[k] = v
  }
  if len(p) == 0 {
    return nil, errors.New("invalid keyword line")
  }
  return p, nil
}
