package main

import (
	"bufio"
	"encoding/xml"
	"os"
	"sort"
	"strings"
)

type Nzb struct {
	Files []File `xml:"file"`
	Info  []Meta `xml:"head>meta"`
}

func (nzb *Nzb) Size() int {
	n := 0
	for _, f := range nzb.Files {
		n += f.Size()
	}
	return n
}

type Meta struct {
	Type  string `xml:"type,attr"`
	Value string `xml:",chardata"`
}

type File struct {
	Subject  string    `xml:"subject,attr"`
	Groups   []string  `xml:"groups>group"`
	Segments []Segment `xml:"segments>segment"`
}

func (f *File) Decode() error {
	fout, err := os.OpenFile(f.Name(), os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	f.Sort()
	for _, s := range f.Segments {
		fin, err := os.Open(s.Name)
		if err != nil {
			if !os.IsNotExist(err) {
				return err
			}
			continue
		}
    defer fin.Close()
		scanner := bufio.NewScanner(fin)
		for scanner.Scan() {
			data := scanner.Bytes()
			if !IsData(data) {
				continue
			}
			if _, err = fout.Write(Decode(data)); err != nil {
				return err
			}
		}
	}
	return nil
}

func (f *File) Name() string {
	i := strings.Index(f.Subject, "\"") + 1
	if i > 0 {
		j := strings.LastIndex(f.Subject, "\"")
		if j > i {
			return strings.TrimSpace(f.Subject[i:j])
		}
	}
	return ""
}

func (f *File) Purge() error {
	for _, s := range f.Segments {
		if err := os.Remove(s.Name); err != nil {
			if !os.IsNotExist(err) {
				return err
			}
		}
	}
	return nil
}

func (f *File) Size() int {
	n := 0
	for _, s := range f.Segments {
		n += s.Bytes
	}
	return n
}

func (f *File) Sort() {
	sort.Sort(ByNumber(f.Segments))
}

type Segment struct {
	Bytes  int    `xml:"bytes,attr"`
	Number int    `xml:"number,attr"`
	Name   string `xml:",chardata"`
}

type ByNumber []Segment

func (by ByNumber) Len() int           { return len(by) }
func (by ByNumber) Less(i, j int) bool { return by[i].Number < by[j].Number }
func (by ByNumber) Swap(i, j int)      { by[i], by[j] = by[j], by[i] }

func OpenNzb(name string) (*Nzb, error) {
	data, err := os.ReadFile(name)
	if err != nil {
		return nil, err
	}
	nzb := &Nzb{}
	if err := xml.Unmarshal([]byte(data), &nzb); err != nil {
		return nil, err
	}
	return nzb, nil
}
