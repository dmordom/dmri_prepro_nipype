'''
Created on June 1, 2015

@author: moreno
'''

#!/usr/bin/env python
"""
=============================================
Diffusion MRI Preprocessing
=============================================
"""

# fslswapdim A_diff_moco.nii -x y z A_diff_moco_NEUROLOGICAL.nii.gz
# fslorient -swaporient A_diff_moco_NEUROLOGICAL.nii
# some_command | tee >(command1) >(command2) >(command3) ... | command4

if __name__ == '__main__':
    
    import sys
    import datetime, time
    from nipype import config
    
    from p1_prepro_t1 import do_p1_prepro_t1
    from p2_prepro_dMRI import do_p2_prepro_dMRI
    from p3_tractscript import script_tracking, trackwait
    from p4_postpro import do_p4_postpro
    from p5_cleanup import do_cleanup, do_wrapup




    cfg = dict(logging=dict(workflow_level = 'DEBUG'), execution={'remove_unnecessary_outputs': False, 'job_finished_timeout': 350, 'stop_on_first_rerun': False, 'stop_on_first_crash': True} )
    config.update_config(cfg)
    
    
    data_template = "%s/%s"
    is_LH = True
    is_RH = False
    pipe_dict = dict([('t1',0),('dmri',1),('track',2),('track_lh',2),('track_rh',3),('post',4)])
    pipe_stop = 5

    
    """
    PIPE VARIABLES BELOW
    """
    
    tract_number = 5000
    tract_step = 0.3
    freesurfer_dir = '/scr/spinat2/moreno_adrian/freesurfer'
    data_dir = '/scr/spinat2/moreno_adrian/original'
    
    
    register_to_mni = False
    use_condor = True
    use_sample= False
    clean = True
    pipe_start = 't1'
    pipe_stop = 5
    pipe_restart= 't1'
    
                    
    subject_list = ["s1_preop"]#,"s1_postop","s2_preop","s2_postop"] # 


    if (use_sample):
        workflow_dir = '/scr/spinat2/moreno_adrian/workflow_sample'
        output_dir = '/scr/spinat2/moreno_adrian/processed_sample'
        chunk_nr = 1
    else:
        workflow_dir = '/scr/spinat2/moreno_adrian/workflow'
        output_dir = '/scr/spinat2/moreno_adrian/processed'
        chunk_nr = 100

    """
    END PIPE VARIABLES
    """
    
    
    start_point = pipe_dict.get(pipe_start,pipe_stop)
    restart_point = pipe_dict.get(pipe_restart,pipe_stop)  

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    loop through the subject list and define the input files.
    For our purposes, these are the dwi image, b vectors, and b values.
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
        
    for subject_id in subject_list:
        
        workflow_1_prepro_t1 = do_p1_prepro_t1(subject_id, freesurfer_dir, data_dir, data_template, workflow_dir, output_dir, register_to_mni)
        workflow_2_prepro_dMRI = do_p2_prepro_dMRI(subject_id, freesurfer_dir, data_dir, data_template, workflow_dir, output_dir)
        workflow_4_postpro = do_p4_postpro(subject_id, freesurfer_dir, workflow_dir, output_dir, tract_number, use_sample)

     
        if (use_condor):
            this_plugin='Condor'
            #this_plugin='CondorDAGMan'
        else:
            this_plugin='Linear'
            
        for i in xrange(pipe_stop):
            if (i<start_point):
                continue
            
            used_plugin = this_plugin
            
            if(i<2 or i>3):
                if(i==0):
                    this_workflow=workflow_1_prepro_t1
                    used_plugin = 'Linear'
                if(i==1):
                    this_workflow=workflow_2_prepro_dMRI
                if(i==4):
                    this_workflow=workflow_4_postpro
                
                cfghash = dict(execution={'hash_method': "content"} )
                config.update_config(cfghash)
                    
                this_workflow.write_graph()
                runtime_err_counter = 0
                while True:
                    try:
                        this_workflow.run(plugin=used_plugin, plugin_args={'block':True})
                        break
                    except IOError as io_error:
                        this_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                        error_message = "***********\nIO EXCEPTION ERROR AT: {0}\nSubject: {1} workflow: {2}, RE-RUNNING WORKFLOW\n{3}\n***********\n".format(this_time, subject_id, i, sys.exc_info())
                        print error_message                     
                        errorlog_file = open(workflow_dir + '/'+ subject_id +'_IO_exceptions.log','a')
                        errorlog_file.write( error_message )
                        errorlog_file.close()
                        raise
                    except RuntimeError as runtime_error:
                        this_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                        error_message = "***********\nRUNTIME EXCEPTION ERROR AT: {0}\nSubject: {1} workflow: {2}, RE-RUNNING WORKFLOW\n{3}\n***********\n".format(this_time, subject_id, i, sys.exc_info())
                        print error_message
                        errorlog_file = open(workflow_dir + '/'+ subject_id +'_runtime_exceptions.log','a')
                        errorlog_file.write( error_message )
                        errorlog_file.close()
                        runtime_err_counter += 1
                        if (runtime_err_counter > 3):
                            raise
                    except:
                        this_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                        error_message = "***********\nUNEXPECTED ERROR AT: {0}\nSubject: {1} workflow: {2}\n{3}\n***********\n".format(this_time, subject_id, i, sys.exc_info())
                        print error_message
                        errorlog_file = open(workflow_dir + '/'+ subject_id +'_unknown_exceptions.log','a')
                        errorlog_file.write( error_message )
                        errorlog_file.close()
                        raise
                if(clean):
                    do_cleanup(i, subject_id, workflow_dir, output_dir)
                    
            else: #its the scripting part
                if(i==2):
                    script_tracking(subject_id, chunk_nr, output_dir, tract_number,tract_step, is_LH, use_sample)
                elif (i==3):
                    script_tracking(subject_id, chunk_nr, output_dir, tract_number,tract_step, is_RH, use_sample)
                    trackwait(subject_id, chunk_nr, output_dir)
        #end if else about which workflow
       
            if(clean and i==4):
                do_wrapup(subject_id, workflow_dir, output_dir)
        start_point = restart_point  #start next subject from first pipeline
        
