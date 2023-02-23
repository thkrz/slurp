package main

import (
	"flag"
  "fmt"
	"log"
	"os"
	"path"
	"strings"
	"sync"
)

var host string
var user string
var pass string
var ssl bool
var num int

var wg sync.WaitGroup

func CutSuffix(s, suffix string) (string, bool) {
	i := strings.LastIndex(s, suffix)
	if i < 0 {
		return s, false
	}
	return s[:i], true
}

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
	for i := range g {
		if err = c.Group(g[i]); err == nil {
			break
		}
	}
	if err != nil {
		log.Panic(err)
	}
	for i := range s {
		data, err := c.Body(s[i].Name)
		if err != nil {
			continue
		}
		if err = os.WriteFile(s[i].Name, data, 0644); err != nil {
			log.Panic(err)
		}
	}
}

func init() {
	log.SetFlags(0)
  log.SetPrefix("slurp: ")

	flag.StringVar(&host, "host", "", "nntp server address")
	flag.StringVar(&user, "user", "", "username")
	flag.StringVar(&pass, "pass", "", "password")
	flag.BoolVar(&ssl, "ssl", false, "use ssl encryption")
	flag.IntVar(&num, "threads", 1, "number of threads")
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
	before, _ := CutSuffix(path.Base(flag.Arg(0)), ".nzb")
	if err = os.Mkdir(before, 0755); err != nil {
		log.Println(err)
	}
	if err = os.Chdir(before); err != nil {
		log.Fatal(err)
	}
  fmt.Println(before)
	N := len(obj.Files)
	for i, f := range obj.Files {
		log.Printf("%d/%d (%s)\n", i+1, N, f.Name())
		if _, err = os.Stat(f.Name()); err == nil {
			continue
		}
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
		wg.Wait()
		func() {
			defer f.Purge()
			if err := f.Decode(); err != nil {
				log.Panic(err)
			}
		}()
	}
}
