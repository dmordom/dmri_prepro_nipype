# THIS FILE SHOULD BE COPIED INTO THE PIPELINE OUTPUT FOLDER

TMP_DIR="${_CONDOR_SCRATCH_DIR}/morenotrack_tmp_${SUBJECT}_${HEMI}_chunk_${CHUNK_NR}"
CSD="${TMP_DIR}/csd.mif"
rm -fr ${TMP_DIR}
mkdir ${TMP_DIR}
cp -f ${OUTPUT_DIR}/diff_model/${SUBJECT}_CSD.mif ${CSD}

if [ "$?" != "0" ]; then
    echo "[Error] copy failed to ${TMP_DIR} folder..." 1>&2
	rm -fr ${TMP_DIR}
	exit 1
fi

echo "working directory is: ${TMP_DIR}"

WM_MASK_NII="${TMP_DIR}/mask_wm.nii"
FULL2COMPACT="/scr/spinat2/moreno_hClustering_project/1_Code/hClustering_2.0/bin/full2compact/full2compact"


if [ "$?" != "0" ]; then
	echo "[Error] copy failed to ${TMP_DIR} csd got copied but not wm masks..." 1>&2
	exit 1
fi

FIRST_SEED=$((${CHUNK_NR}*${SEEDS_PER_FILE}))
TRACK_MAX=$((${TRACK_COUNT}*2))
CURRENT_SEED=${FIRST_SEED}
SEED_FILE="chunk_${CHUNK_NR}.txt"

TMP_LOG=${TMP_DIR}/${SUBJECT}_${HEMI}_chunk_${CHUNK_NR}.log
FINAL_LOG=${CHUNKS_DIR}/logs/${SUBJECT}_${HEMI}_chunk_${CHUNK_NR}.log

cd ${TMP_DIR}
mkdir ${TMP_DIR}/raw
mkdir ${TMP_DIR}/log


cp -f ${OUTPUT_DIR}/fa_masking/${SUBJECT}_mask_wm.nii ${WM_MASK_NII}
cp -f ${CHUNKS_DIR}/seeds/${SEED_FILE} ${TMP_DIR}/${SEED_FILE}

DIRECT_SUCCESS=0
RECOVERED_SUCCESS=0
COMPLETE_FAILS=0
ADDED_FAILS=0

echo "start-time | finish-time | direct-success | recovered-success | complete-fail | added-fails " &> ${TMP_LOG}

date +"%T.%N" &>> ${TMP_LOG}


RAW_LIST="${TMP_DIR}/raw/rawtract_list.txt"

while read COORDLINE; do
	echo "id: ${CURRENT_SEED}, data: ${COORDLINE}"
	ID=${CURRENT_SEED}
	TRACK_FAILED=1
	FAILED_ATTEMPTS=0
	while [ ${TRACK_FAILED} -eq 1 -a ${FAILED_ATTEMPTS} -lt 2 ]; do
		rm -f ${TMP_DIR}/track_${ID}.tck ${TMP_DIR}/raw/probtract_${ID}.nii
		streamtrack -seed ${COORDLINE} -number ${TRACK_COUNT} -initcutoff 0.15 -maxnum ${TRACK_MAX} -mask ${WM_MASK_NII} -step ${STEP} SD_PROB ${CSD} ${TMP_DIR}/track_${ID}.tck
		tracks2prob -template ${WM_MASK_NII} -datatype float32 ${TMP_DIR}/track_${ID}.tck ${TMP_DIR}/raw/probtract_${ID}.nii

		FINAL_TRACKS=$(fslstats ${TMP_DIR}/raw/probtract_${ID}.nii -R | awk '{print $2}')
		TRACK_FAILED=$(( $(bc <<< "${FINAL_TRACKS} < ${TRACK_COUNT}") ))
		FAILED_ATTEMPTS=$((${FAILED_ATTEMPTS}+${TRACK_FAILED}))
	done



	rm -f ${TMP_DIR}/track_${ID}.tck
	CURRENT_SEED=$((${CURRENT_SEED}+1))

	if [ ${FAILED_ATTEMPTS} -eq 0 ] ; then
		DIRECT_SUCCESS=$((${DIRECT_SUCCESS}+1))
	elif [ ${TRACK_FAILED} -eq 0 ] ; then
		RECOVERED_SUCCESS=$((${RECOVERED_SUCCESS}+1))
		ADDED_FAILS=$((${ADDED_FAILS}+${FAILED_ATTEMPTS}))
	else
		COMPLETE_FAILS=$((${COMPLETE_FAILS}+1))
		ADDED_FAILS=$((${ADDED_FAILS}+${FAILED_ATTEMPTS}))
	fi

	chmod a-x ${TMP_DIR}/raw/probtract_${ID}.nii
	
	cp ${TMP_DIR}/raw/probtract_${ID}.nii ${OUTPUT_DIR}/raw_tracts${POSTFIX}/${HEMI}/
	echo "${TMP_DIR}/raw/probtract_${ID}.nii" >> ${RAW_LIST}

done < ${TMP_DIR}/${SEED_FILE}

${FULL2COMPACT} -f ${RAW_LIST} -m ${WM_MASK_NII} -s ${TRACK_COUNT} -l ${TMP_DIR}/log/ -p 1 --nosuffix
chmod -R 777 ${TMP_DIR}/log/
mv -f ${TMP_DIR}/log/* ${OUTPUT_DIR}/compact_tracts${POSTFIX}/${HEMI}/


date +"%T.%N" &>> ${TMP_LOG}
echo "${DIRECT_SUCCESS}" &>> ${TMP_LOG}
echo "${RECOVERED_SUCCESS}" &>> ${TMP_LOG}
echo "${COMPLETE_FAILS}" &>> ${TMP_LOG}
echo "${ADDED_FAILS}" &>> ${TMP_LOG}


mv -f ${TMP_LOG} ${FINAL_LOG}
rm -fr ${TMP_DIR}








