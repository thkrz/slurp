#!/bin/sh

user=
pass=
host=

path="."
cmd="slurp -host $host -ssl -user $user -pass $pass -threads 60"

usage() {
	echo "nzbslurp: [-m] [FILE]" >&2
	exit 1
}

unpack() {
  # fancy unpacking
	unrar x $(ls .part*.rar | head -n 1)
}

nzbget() {
	targ=$(basename "$1" .nzb)
	if [ ! -d "$targ" ]; then
		mkdir "$targ"
	fi
	cd "$targ"
	$cmd ../"$1"
	unpack
	cd ..
}

mflag=false
while getopts ":m" opt; do
	case $opt in
	m)
		mflag=true
		;;
	?)
		usage
		;;
	esac
done
shift $((OPTIND - 1))

if [ $# -eq 1 ]; then
	nzbget "$1"
	exit $?
fi

if $mflag; then
	inotifywait -m $path -e create -e moved_to |
		while read -r d a f; do
			if [ ! "${f: -4}" = ".nzb" ]; then
				continue
			fi
			nzbget "$f"
		done
else
	for f in $path/*.nzb; do
		nzbget "$f"
	done
fi
