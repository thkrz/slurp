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

func (nzb *Nzb) Size() uint64 {
	var n uint64

	for _, f := range nzb.Files {
		n += f.Size()
	}
	return n
}

func (nzb *Nzb) Sort() {
	sort.Sort(BySuffix(nzb.Files))
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
	var fout *os.File

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
		if scanner.Scan() {
			hdr, err := ParseKeywordLine(scanner.Text())
			if err != nil {
				return err
			}
			fout, err = os.OpenFile(hdr["name"], os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
			if err != nil {
				return err
			}
			if _, exists := hdr["part"]; !exists {
				scanner.Scan()
			}
		}
		for scanner.Scan() {
			data := scanner.Bytes()
			if !IsData(data) {
				break
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

func (f *File) Size() uint64 {
	var n uint64

	for _, s := range f.Segments {
		n += s.Bytes
	}
	return n
}

func (f *File) Sort() {
	sort.Sort(ByNumber(f.Segments))
}

type BySuffix []File

func (by BySuffix) Len() int           { return len(by) }
func (by BySuffix) Less(i, j int) bool { return !strings.HasSuffix(by[i].Name(), ".par2") }
func (by BySuffix) Swap(i, j int)      { by[i], by[j] = by[j], by[i] }

type Segment struct {
	Bytes  uint64 `xml:"bytes,attr"`
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
	nzb.Sort()
	return nzb, nil
}
