'''
Created on Oct 17, 2013

@author: moreno
'''

"""
threshold b values in bval file lower than thr to 0
"""
def script_tracking(subject_ID, chunk_nr, output_dir, tract_number,tract_step, is_left, use_sample=False, postfix=''):
    import numpy as np
    from subprocess import call
    import os.path as op
    import time 
    from paux import write_sequence_file
    from paux import fetch_sample
    from paux import image_dims



    if (is_left):
        hemi_string = 'lh'
        side_string = 'left'
    else:
        hemi_string = 'rh'
        side_string = 'right'
        
    
        
    seed_filename = output_dir+'/'+subject_ID+'/fa_masking/'+subject_ID+'_interface_'+side_string+'_mrtrix.txt'
    voxel_filename = output_dir+'/'+subject_ID+'/fa_masking/'+subject_ID+'_interface_'+side_string+'_voxels.txt'

    fa_filename = output_dir+'/'+subject_ID+'/fa_masking/'+subject_ID+'_fa_masked.nii'
    script_dir = output_dir+'/'+subject_ID+'/track_scripts'+postfix+'/'
    chunk_dir=script_dir+hemi_string+'_chunks'
    seeds_dir=chunk_dir+"/seeds"
    call("mkdir "+script_dir, shell=True)
    call("mkdir "+chunk_dir, shell=True)
    call("mkdir "+seeds_dir, shell=True)
    
    if(is_left):
        call("mkdir "+output_dir+"/"+subject_ID+"/raw_tracts"+postfix, shell=True)
        call("mkdir "+output_dir+"/"+subject_ID+"/compact_tracts"+postfix, shell=True)
        
    call("mkdir "+output_dir+"/"+subject_ID+"/raw_tracts"+postfix+"/"+hemi_string, shell=True)
    
    chunk_file_prefix=seeds_dir+'/chunk_'
    
    
    print("preparing for tracking of "+side_string+" hemisphere of subject "+subject_ID)


    all_seed_coords = fetch_sample(seed_filename, use_sample)
    out_sequence_filename=output_dir+"/"+subject_ID+"/compact_tracts"+postfix+"/"+subject_ID + "_" + side_string + ".txt"
    write_sequence_file(all_seed_coords,out_sequence_filename)


    if( use_sample ):
        all_seed_voxels = fetch_sample(voxel_filename, use_sample)
        dimensions = image_dims(fa_filename)
        out_roi_filename = output_dir+"/"+subject_ID+"/compact_tracts"+postfix+"/"+subject_ID + "_treeroi_sample_" + side_string + ".txt"
        
        
        temp_roi_filename = "/tmp/"+subject_ID + "_treeroi_" + side_string + ".txt"
        np.savetxt(temp_roi_filename, np.array(all_seed_voxels), fmt='%d', delimiter=' ')
        
        temp_trackid_filename = "/tmp/"+subject_ID + "_treetrackids_" + side_string + ".txt"
        trackid_array = np.arange(all_seed_voxels.shape[0])
        np.savetxt(temp_trackid_filename, trackid_array, fmt='%d', delimiter='\n')

    
        with open(out_roi_filename, 'w+') as roi_file:
            roi_file.write("#imagesize\n")
            roi_file.write(str(dimensions[0])+" "+str(dimensions[1])+" "+str(dimensions[2])+" nifti\n")
            roi_file.write("#endimagesize\n\n")
            roi_file.write("#streams\n")
            roi_file.write(str(tract_number)+"\n")
            roi_file.write("#endstreams\n\n")
            roi_file.write("#trackindex\n")
            with open(temp_roi_filename, "r")as index_file:
                roi_file.write(index_file.read())
            roi_file.write("#endtrackindex\n")
            roi_file.write("#roi\n")
            with open(temp_roi_filename, "r")as roi_file:
                roi_file.write(roi_file.read())
            roi_file.write("#endroi\n")
    

    chunk_size = int(np.ceil(float(len(all_seed_coords))/chunk_nr))
    for i in xrange(chunk_nr):
        start_seed = i*chunk_size
        if (i==chunk_nr-1):
            end_seed = len(all_seed_coords)
        else:
            end_seed = (i+1)*chunk_size
        this_chunk = all_seed_coords[start_seed:end_seed]
        this_chunk_filename=chunk_file_prefix+str(i)+'.txt'
        np.savetxt(this_chunk_filename, this_chunk, fmt='%f', delimiter=',')
    

    
    print("created "+str(chunk_nr)+" tracking chunks with "+str(chunk_size)+" seeds each")
    
    subject_line='SUBJECT="'+subject_ID+'"'
    seedxfile_line="SEEDS_PER_FILE="+str(chunk_size)
    hemi_line='HEMI="'+hemi_string+'"'
    trackcount_line='TRACK_COUNT="'+str(tract_number)+'"'
    trackcstep_line='STEP="'+str(tract_step)+'"'
    chunksdir_line='CHUNKS_DIR="'+chunk_dir+'"'
    outdir_line='OUTPUT_DIR="'+output_dir+'/'+subject_ID+'"'
    postfix_line='POSTFIX="'+postfix+'"'


    
    script_filename=chunk_dir+"/script_chunk"".sh"

    with open(script_filename, 'w+') as script_file:
        with open(output_dir+"/track_script_header.sh", "r") as header_file:
            script_file.write(header_file.read())
        script_file.write(subject_line+"\n")
        script_file.write(seedxfile_line+"\n")
        script_file.write(hemi_line+"\n")
        script_file.write(trackcount_line+"\n")
        script_file.write(trackcstep_line+"\n")
        script_file.write(chunksdir_line+"\n")
        script_file.write(outdir_line+"\n")
        script_file.write(postfix_line+"\n")

        with open(output_dir+"/track_script_body.sh", "r")as body_file:
            script_file.write(body_file.read())
            
            
    print("tracking script created in: "+ script_filename)

            
    submit_filename =  script_dir+subject_ID+"_"+hemi_string+"_tocondor.submit"        
    with open(submit_filename, "w") as submitter_file:
        submitter_file.write('executable = '+script_filename+'\n')
        submitter_file.write('getenv = True\nuniverse = vanilla\nrequest_memory = 500\nrequest_disk = 500000\nrequest_cpus = 1\nnotification = Error\n\n')
#        submitter_file.write('requirements = Machine == "kalifornien.cbs.mpg.de"\n\n')  
        for i in xrange(chunk_nr):
            submitter_file.write("arguments = "+str(i)+"\n")
            submitter_file.write("output = "+chunk_dir+"/logs/op_chunk_"+str(i)+".out\n")
            submitter_file.write("error = "+chunk_dir+"/logs/op_chunk_"+str(i)+".error\n")
            submitter_file.write("log = "+chunk_dir+"/logs/op_chunk_"+str(i)+".log\n")
            submitter_file.write("queue\n\n")
            
    print("condor submitter file created in: "+ submit_filename)

            
    call("chmod a+x "+script_filename, shell=True)
    call("mkdir "+chunk_dir+"/logs", shell=True)
    

    
    print("Submitting "+submit_filename+"...\n")
#    call("condor_submit "+submit_filename, shell=True)
    
    
def trackwait(subject_ID, chunk_nr, output_dir,postfix=''):
    from subprocess import call
    import os.path as op
    import time 

    script_dir = output_dir+'/'+subject_ID+'/track_scripts'+postfix+'/'

    
    print("Waiting for tracking scripts to finish...")
    still_running=True
    while(still_running):
        still_running=False
        for this_chunk in xrange(chunk_nr):
            success_log_filename_lh=script_dir+"lh_chunks/logs/"+subject_ID+"_lh_chunk_"+str(this_chunk)+".log"
            success_log_filename_rh=script_dir+"rh_chunks/logs/"+subject_ID+"_rh_chunk_"+str(this_chunk)+".log"
            if ( (not op.isfile(success_log_filename_lh)) or (not op.isfile(success_log_filename_rh)) ):
                still_running=True
                break
            #end if
        #end for
        time.sleep(10) 
    #end while
    call("gzip -f "+script_dir+"/[lr]h_chunks/logs/op_chunk_*.error", shell=True)
    print("All tracks finished! continuing workflow...\n")
#end if

                
    
                


    
    