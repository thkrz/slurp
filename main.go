package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
)

var host string
var num int
var pass string
var ssl bool
var user string

var ch chan uint64
var wg sync.WaitGroup

func fetch(s []Segment, g []string) {
	defer wg.Done()

	c, err := Connect(host, ssl)
	if err != nil {
		log.Panic(err)
	}
	defer c.Close()
	if err = c.Auth(user, pass); err != nil {
		log.Panic(err)
	}
	for i := range s {
		for j := range g {
			if err = c.Group(g[j]); err != nil {
				continue
			}
			data, err := c.Body(s[i].Name)
			if err != nil {
				continue
			}
			ch <- s[i].Bytes
			if err = os.WriteFile(s[i].Name, data, 0644); err != nil {
				log.Panic(err)
			}
			break
		}
	}
	if err != nil {
		log.Panic(err)
	}
}

func progress(size uint64) {
	var total uint64

	st := time.Now()
	for total < size {
		n := <-ch
		total += n
		perc := (100 * total) / size
		speed := float64(total) / float64(time.Since(st).Microseconds())
		fmt.Fprintf(os.Stderr, "%12d\t%3d%%\t%5.1f MB/s\r", total, perc, speed)
	}
	os.Stderr.WriteString("\n")
}

func init() {
	log.SetFlags(0)
	log.SetPrefix("slurp: ")

	flag.StringVar(&host, "host", "", "nntp server address")
	flag.StringVar(&user, "user", "", "username")
	flag.StringVar(&pass, "pass", "", "password")
	flag.BoolVar(&ssl, "ssl", false, "use ssl encryption")
	flag.IntVar(&num, "threads", 1, "number of threads")

	ch = make(chan uint64)
}

func main() {
	flag.Parse()
	if flag.NArg() < 1 {
		log.Fatal("no input file")
	}

	obj, err := OpenNzb(flag.Arg(0))
	if err != nil {
		log.Fatal(err)
	}
	N := len(obj.Files)
	for i, f := range obj.Files {
		name := f.Name()
		fmt.Fprintf(os.Stderr, "[%d/%d] %s\n", i+1, N, name)
		// if _, err = os.Stat(name); err == nil {
		// 	continue
		// }
		n := len(f.Segments)
		k := (n + num - 1) / num
		for j := 0; j < n; j += k {
			end := j + k
			if end > n {
				end = n
			}
			wg.Add(1)
			go fetch(f.Segments[j:end], f.Groups)
		}
		go progress(f.Size())
		wg.Wait()
		func() {
			defer f.Purge()
			if err := f.Decode(); err != nil {
				log.Panic(err)
			}
		}()
	}
}
