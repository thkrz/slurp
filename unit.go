package main

var si_units = []string{"", "kB", "MB", "GB", "TB", "PB"}

func SIUnit(n float64) (float64, string) {
	i := 0
	for ; n > 1000.0; i++ {
		n /= 1000.0
	}
	return n, si_units[i]
}

func TimeUnit(n uint64) (uint64, uint64, uint64) {
	h := n / 3600
	m := (n - h*3600) / 60
	s := (n - h*3600 - m*60)
	return h, m, s
}
