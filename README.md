# FFMPEG Param

## Intel QSV

    ffmpeg -ss %d -t %d -i %s -c:v h264_qsv -global_quality 25 -c:a aac -strict experimental %s -loglevel warning

## AMD AMF

    ffmpeg -ss %d -t %d -i %s -c:v h264_amf -global_quality 25 -c:a aac -strict experimental %s -loglevel warning

# YIKE_DIR

## genshin
    
split with ffmpeg (sf) for genshin record.

## R (departed via R_OriginQulity)

split with ffmpeg and encrypt for R18 movie. 

## record (departed via R and genshin)

split and encrypt for R18 and genshin.