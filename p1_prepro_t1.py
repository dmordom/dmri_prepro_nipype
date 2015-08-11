'''
Created on Oct 17, 2013

@author: moreno and kanaan
'''

#!/usr/bin/env python
"""
=============================================
Diffusion MRI Preprocessing
=============================================
"""

def do_p1_prepro_t1(subject_ID, freesurfer_dir, data_dir, data_template, workflow_dir, output_dir, register_to_mni = False):

    
    """
    Packages and Data Setup
    =======================
    Import necessary modules from nipype.
    """
    
    
    import nipype.interfaces.io as io  # Data i/o
    import nipype.interfaces.utility as util  # utility
    import nipype.pipeline.engine as pe  # pipeline engine
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.freesurfer as fsurf  # freesurfer
    import nipype.interfaces.ants as ants
    import os.path as op  # system functions
    
    from nipype.interfaces.utility import Function
    from paux import aff2rigid
    

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    Point to the freesurfer subjects directory (Recon-all must have been run on the subjects)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    subjects_dir = op.abspath(freesurfer_dir)
    fsurf.FSCommand.set_default_subjects_dir(subjects_dir)
    fsl.FSLCommand.set_default_output_type('NIFTI')
    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    define the workflow(s)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    t12mni_pipeline = pe.Workflow(name='p1_prepro_t12mni')

    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    Use datasource node to perform the actual data grabbing.
    Templates for the associated images are used to obtain the correct images.
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    info = dict(t1=[['subject_id', 't1.nii.gz']])
    
    datasource = pe.Node(interface=io.DataGrabber(infields=['subject_id'], outfields=info.keys()), name='datasource')
    datasource.inputs.subject_id =  subject_ID
    datasource.inputs.template = data_template
    datasource.inputs.base_directory = data_dir
    datasource.inputs.template_args = info
    datasource.inputs.sort_filelist = True
    datasource.run_without_submitting = True
    
    auxsource = pe.Node(interface=io.DataGrabber(outfields=['mni152']), name='auxsource')
    auxsource.inputs.template = 'MNI152_T1_1mm_brain.nii.gz'
    auxsource.inputs.base_directory = '/usr/share/fsl/data/standard/'
    auxsource.inputs.sort_filelist = True
    auxsource.run_without_submitting = True
    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["t1","mni152"]), name="inputnode")
    
#     FreeSurferSource = pe.Node(interface=io.FreeSurferSource(), name='01_FreeSurferSource')
#     FreeSurferSource.inputs.subjects_dir = subjects_dir
#     FreeSurferSource.inputs.subject_id = subject_ID
#     FreeSurferSource.run_without_submitting = True
    
    """
    eliminate field bias in t1 image
    """
    input_rename = pe.Node(util.Rename(format_string=subject_ID +'_t1_original.nii.gz'), name='00_input_rename')
    t12mni_pipeline.connect(inputnode, "t1", input_rename, "in_file")
    
    corrected_t1 = pe.Node(interface=ants.N4BiasFieldCorrection(), name='01_corrected_t1')
    corrected_t1.inputs.output_image = subject_ID + '_t1.nii'
    corrected_t1.inputs.dimension = 3
    corrected_t1.inputs.bspline_fitting_distance = 300
    corrected_t1.inputs.shrink_factor = 3
    corrected_t1.inputs.n_iterations = [50,50,30,20]
    corrected_t1.inputs.convergence_threshold = 1e-6
    corrected_t1.run_without_submitting = True
    t12mni_pipeline.connect(inputnode, "t1", corrected_t1, "input_image")    

    
    """
    skull strip t1 image for better registration
    """
    
    bet_t1 = pe.Node(interface=fsl.BET(mask=False), name='02_bet_t1')
    bet_t1.run_without_submitting = True
    t12mni_pipeline.connect(corrected_t1, "output_image", bet_t1, "in_file")
    
    """
    register with dof 12 skull stripped t1 to mni for standard orientation
    """
    flirt_t1_dof12_2_mni = pe.Node(interface=fsl.FLIRT(), name='03_flirt_t1_dof12_2_mni')
    flirt_t1_dof12_2_mni.inputs.dof = 12
    flirt_t1_dof12_2_mni.inputs.cost_func = 'corratio'
    flirt_t1_dof12_2_mni.inputs.bins = 256
    flirt_t1_dof12_2_mni.inputs.interp = 'trilinear'
    flirt_t1_dof12_2_mni.inputs.out_matrix_file = 'flirt_dof12_t1_2_mni.mat'
    flirt_t1_dof12_2_mni.run_without_submitting = True
    t12mni_pipeline.connect(bet_t1, "out_file", flirt_t1_dof12_2_mni,"in_file")
    t12mni_pipeline.connect(inputnode, "mni152",flirt_t1_dof12_2_mni, "reference")
    
    flirt_t1_2_mni_aff2rigid = pe.Node(interface=Function(input_names=["in_mat","out_mat"],output_names=["out_file"],function=aff2rigid), name='04_flirt_t1_2_mni_aff2rigid')
    flirt_t1_2_mni_aff2rigid.inputs.out_mat= subject_ID +'_t1_2_mni_aff2rigid.mat'
    flirt_t1_2_mni_aff2rigid.run_without_submitting = True
    t12mni_pipeline.connect(flirt_t1_dof12_2_mni, "out_matrix_file", flirt_t1_2_mni_aff2rigid,"in_mat")

    """
    we use the registration matrix to convert the unstripped image to mni (freesurfer skull stripping works better in my experience
    """

    flirt_t1_2_mni = pe.Node(interface=fsl.ApplyXfm(), name='05_flirt_t1_2_mni')
    flirt_t1_2_mni.inputs.apply_xfm = True
    flirt_t1_2_mni.inputs.interp = 'trilinear'
    flirt_t1_2_mni.inputs.out_file = subject_ID + '_t1_mni.nii'
    flirt_t1_2_mni.run_without_submitting = True
    t12mni_pipeline.connect(corrected_t1, "output_image",flirt_t1_2_mni , "in_file")
    t12mni_pipeline.connect(flirt_t1_2_mni_aff2rigid, "out_file", flirt_t1_2_mni ,"in_matrix_file")
    t12mni_pipeline.connect(inputnode, "mni152", flirt_t1_2_mni , "reference")
    
    reconall = pe.Node(interface=fsurf.ReconAll(), name="06_reconall")
    reconall.inputs.directive = 'all'
    reconall.inputs.subject_id = subject_ID
    reconall.inputs.subjects_dir = subjects_dir
    if( register_to_mni ):
        t12mni_pipeline.connect(flirt_t1_2_mni , "out_file",reconall, "T1_files")
    else:
        t12mni_pipeline.connect(corrected_t1 , "output_image",reconall, "T1_files")

    """
    use a sink to save outputs
    """
    
    datasink = pe.Node(io.DataSink(), name='99_datasink')
    datasink.inputs.base_directory = output_dir
    datasink.inputs.container = subject_ID
    datasink.inputs.parameterization = True
    datasink.run_without_submitting = True
     
    t12mni_pipeline.connect(input_rename, 'out_file', datasink, 't1')
    t12mni_pipeline.connect(corrected_t1, 'output_image', datasink, 't1.@1')
    t12mni_pipeline.connect(flirt_t1_2_mni_aff2rigid, 'out_file', datasink, 't1.@2')
    t12mni_pipeline.connect(flirt_t1_2_mni, 'out_file', datasink, 't1.@3')
    t12mni_pipeline.connect(inputnode, 'mni152', datasink, 't1.@4')


    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    ===============================================================================
    Connecting the workflow
    ===============================================================================
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    
    """
    Create a higher-level workflow
    ------------------------------
    Finally, we create another higher-level workflow to connect our t12mni_pipeline workflow with the info and datagrabbing nodes
    declared at the beginning. Our tutorial is now extensible to any arbitrary number of subjects by simply adding
    their names to the subject list and their data to the proper folders.
    """
    
    connectprepro = pe.Workflow(name="p1_prepro_t1")
    
    connectprepro.base_dir = op.abspath(workflow_dir + "/workflow_"+subject_ID )
    
    connectprepro.connect([(datasource, t12mni_pipeline, [('t1', 'inputnode.t1')]),
                               (auxsource, t12mni_pipeline, [('mni152', 'inputnode.mni152')])])

    return connectprepro
