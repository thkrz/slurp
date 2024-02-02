package main

import "fmt"

var unit = []string{"", "kB", "MB", "GB", "TB", "PB"}

func FormatSize(n uint64) string {
	i := 0
	for ; n > 1000; i++ {
		n /= 1000
	}
	return fmt.Sprintf("%d %s", n, unit[i])
}
