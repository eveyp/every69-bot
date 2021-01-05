#! /usr/bin/zsh

newfile="combined_addresses.csv"
[[ -a $newfile ]] && rm $newfile
files=(*/*.csv)
counter=1
for i in $files; do
    state=$(dirname $i)

    place=$(basename $i .csv)
    place=${place:u}
    place=${place//_/ }

    echo parsing file $counter of $#files: ${place:l}, ${state:l}
    #awk -F, '$3 ~ /^69$/ {print}' $i > $newfile
    [[ $counter == 1 ]] && head $i -n 1 > $newfile
    ((counter++))

    [[ ($place[1,7] == "CITY OF") ]] && sed 1d $i | awk -F, -vcity="${place##CITY OF }" -$
    [[ ($place[1,7] != "CITY OF") ]] && sed 1d $i | awk -F, -vstate="${state:u}" '{$8=sta$done
done