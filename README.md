# Name
slurp - nzb downloader
# Synopsis
`$ slurp [-ssl] [-threads num] [-u user [-p password]] -h host[:port] nzb [file...]`

`$ slurp -list nzb`
# Description
The *slurp* utility reads a *nzb* file and downloads all files, or only the ones
specified in *file*.
# Options
The following options are supported

<dl>
  <dt><strong>-list</strong></dt>
  <dd>List files in NZB</dd>
  <dt><strong>-ssl</strong></dt>
  <dd> Turn on ssl support (Default: off)</dd>
  <dt><strong>-threads</strong> number</dt>
  <dd>Number of download threads (Default: 10)</dd>
  <dt><strong>-u</strong> username</dt>
  <dd>Login username</dd>
  <dt><strong>-p</strong> password</dt>
  <dd>Login password</dd>
  <dt><strong>-h</strong> hostname[:port]</dt>
  <dd>NNTP server hostname with optional port number</dd>
</dl>

# Operands
The following operands are supported

<dl>
  <dt>nzb</dt>
  <dd>NZB file</dd>
  <dt>file</dt>
  <dd>File to be downloaded from NZB, can use UNIX globbing</dd>
</dl>

