package main

import "fmt"

var unit = []string{"", "kB", "MB", "GB", "TB", "PB"}

func FormatSize(n float64) string {
	i := 0
	for ; n > 1000.0; i++ {
		n /= 1000.0
	}
	return fmt.Sprintf("%5.1f %s", n, unit[i])
}
