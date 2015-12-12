#!/usr/bin/env python3

import sys
import os
import subprocess
import argparse

def main():
    argparser = argparse.ArgumentParser(
        description='convert 3D videos from horizontally to vertically aligned')
    argparser.add_argument('--ffmpeg', default='ffmpeg', help='path to ffmpeg binary')
    argparser.add_argument('file', help='file to convert')
    args = argparser.parse_args()
    
    in_file = args.file

    if '.' not in in_file:
        print("need filename with extension")
        return
        
    suffix = in_file[in_file.rindex('.'):]
    basename = os.path.basename(in_file)
    basename = basename[:basename.rindex('.')]
    out_file = basename + '_3dv' + suffix
    meta_file = basename + '_3dv' + '.txt'
    ffmpeg_bin = args.ffmpeg
    
    command = ['time', ffmpeg_bin, '-i', in_file, '-filter_complex',  
        "[0:v]crop=in_w/2:in_h:0:0 [top]; "
        "[0:v]crop=in_w/2:in_h:in_w/2:0[bottom]; "
        "[top][bottom]vstack,pad=in_h:in_h:(in_h-in_w)/2:0:black[outv]", 
        '-map', "[outv]", 
        '-map', '0:a', 
        '-c:a', 'copy', 
        '-b:v', '20M', 
        out_file]
    
    print("in_file:    ", in_file)
    print("out_file:   ", out_file)
    print("meta_file:  ", meta_file)
    print("ffmpeg_bin: ", ffmpeg_bin)
    print("command:    ", command)
    
    subprocess.call(command)
    
    with open(meta_file, 'w') as metafile:
        metafile.write('{\n"title": "%s",\n"format": "3DTB"\n}\n' % basename)

if __name__ == '__main__':
    main()


'''
Realign LR -> TB
ffmpeg -i input.mp4 -filter_complex "\
  [0:v]crop=in_w/2:in_h:0:0 [top]; \
  [0:v]crop=in_w/2:in_h:in_w/2:0[bottom]; \
  [top][bottom]vstack[outv]" \
  -map "[outv]" -map 0:a -c:a copy -b:v 1M output.mp4


Pad to same width as height:
ffmpeg -i input.mp4 -vf "pad=width=in_h:height=in_h:x=in_w/2:y=0:color=black" -c:a copy output.mp4


Scale:
ffmpeg -i input.mp4 -vf scale=iw/2:-1 -c:a copy output.mp4


Realign and pad to same width as height:
ffmpeg -i input.mp4 -filter_complex "\
    [0:v]crop=in_w/2:in_h:0:0 [top]; \
    [0:v]crop=in_w/2:in_h:in_w/2:0[bottom]; \
    [top][bottom]vstack,pad=in_h*2:in_h*2:(in_h-in_w*0.25):0[outv]" \
    -map "[outv]" -map 0:a -c:a copy -b:v 20M output.mp4


Realign and pad to same width as height:
ffmpeg -i input.mp4 -filter_complex "\
    [0:v]crop=in_w/2:in_h:0:0 [top]; \
    [0:v]crop=in_w/2:in_h:in_w/2:0[bottom]; \
    [top][bottom]vstack,\
    scale=iw*min(2000/iw\,2000/ih):ih*min(2000/iw\,2000/ih), \
    pad=2000:2000:(ow-iw)/2:(oh-ih)/2[outv]" \
    -map "[outv]" -map 0:a -c:a copy -b:v 20M output.mp4

'''
