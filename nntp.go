package main

import (
	"crypto/tls"
	"net"
	"net/textproto"
)

type Client struct {
	conn net.Conn
	io   *textproto.Conn
}

func Connect(addr string, useEncryption bool) (*Client, error) {
	var err error

	c := new(Client)
	if useEncryption {
		c.conn, err = tls.Dial("tcp", addr, nil)
	} else {
		c.conn, err = net.Dial("tcp", addr)
	}
	if err == nil {
		c.io = textproto.NewConn(c.conn)
		_, _, err = c.io.ReadCodeLine(20)
	}
	return c, err
}

func (c *Client) Auth(user, pass string) error {
	if err := c.Cmd(381, "AUTHINFO USER %s", user); err != nil {
		return err
	}
	return c.Cmd(281, "AUTHINFO PASS %s", pass)
}

func (c *Client) Body(id string) ([]byte, error) {
	if err := c.Cmd(222, "BODY <%s>", id); err != nil {
		return nil, err
	}
	return c.io.ReadDotBytes()
}

func (c *Client) Cmd(expectedCode int, s string, args ...any) error {
	err := c.io.PrintfLine(s, args...)
	if err == nil {
		_, _, err = c.io.ReadCodeLine(expectedCode)
	}
	return err
}

func (c *Client) Group(name string) error {
	return c.Cmd(211, "GROUP %s", name)
}

func (c *Client) Close() error {
	if err := c.Cmd(205, "QUIT"); err != nil {
		return err
	}
	return c.io.Close()
}
