'''
Created on Oct 17, 2013

@author: moreno and kanaan
'''

#!/usr/bin/env python
"""
=============================================
Diffusion MRI Probabiltic tractography on NKI_enhanced.

This script uses FSL and MRTRIX algorithms to generate probabilstic tracts, tract density images
and  a 3D trackvis file of NKI_enhanced data.
=============================================
"""

def do_p4_postpro(subject_ID, freesurfer_dir, workflow_dir, output_dir, tract_number, use_sample=False, postfix=''):

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

    from paux import test_tracts
    from paux import surf2file
    from paux import voxels2nii
    from paux import normalize_matrix
    from paux import interface2surf
    from paux import fetch_sample
    from paux import downsample_matrix
    from paux import merge_matrices
    from paux import get_voxels
    from paux import write_tree_roi

    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    Point to the freesurfer subjects directory (Recon-all must have been run on the subjects)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    subjects_dir = op.abspath(freesurfer_dir)
    fsurf.FSCommand.set_default_subjects_dir(subjects_dir)
    fsl.FSLCommand.set_default_output_type('NIFTI')
    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    define the workflow
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    dmripipeline = pe.Workflow(name = 'p4_postpro' )
    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    Use datasource node to perform the actual data grabbing.
    Templates for the associated images are used to obtain the correct images.
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    
    data_template = subject_ID + "/%s/" + "%s" + "%s"
    
    info = dict(wm = [['fa_masking', subject_ID, '_mask_wm.nii']],
                seeds_left = [['fa_masking', subject_ID, '_interface_left_voxels.txt']],
                seeds_right = [['fa_masking', subject_ID, '_interface_right_voxels.txt']],
                index_left = [['fa_masking', subject_ID, '_interface_left_index.nii']],
                index_right = [['fa_masking', subject_ID, '_interface_right_index.nii']],
                fa = [['fa_masking', subject_ID, '_fa_masked.nii']],
                t1 = [['anatomy', subject_ID, '_t1_masked.nii']],
                inv_flirt_mat = [['anatomy', '', 'flirt_t1_2_fa_inv.mat']],
                warp = [['anatomy', '', 'ants_fa_2_regt1_Warp.nii.gz']])
    
    
    datasource = pe.Node(interface=io.DataGrabber(outfields=info.keys()), name='datasource')
    datasource.inputs.template = data_template
    datasource.inputs.base_directory = output_dir
    datasource.inputs.template_args = info
    datasource.inputs.sort_filelist = True
    datasource.run_without_submitting = True
    
    tracts_left_source = pe.Node(interface=io.DataGrabber(outfields=['tracts_left']), name='tracts_left_source')
    tracts_left_source.inputs.template = subject_ID + '/raw_tracts'+postfix+'/lh/probtract_*.nii'
    tracts_left_source.inputs.base_directory = output_dir
    tracts_left_source.inputs.sort_filelist = True
    tracts_left_source.run_without_submitting = True
    
    tracts_right_source = pe.Node(interface=io.DataGrabber(outfields=['tracts_right']), name='tracts_right_source')
    tracts_right_source.inputs.template = subject_ID + '/raw_tracts'+postfix+'/rh/probtract_*.nii'
    tracts_right_source.inputs.base_directory = output_dir
    tracts_right_source.inputs.sort_filelist = True
    tracts_right_source.run_without_submitting = True
  
    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    The input node declared here will be the main
    conduits for the raw data to the rest of the processing pipeline.
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["wm", "seeds_left", "seeds_right", "index_left", "index_right", "fa", "t1", "inv_flirt_mat", "warp", "tracts_left", "tracts_right"]), name="inputnode")
    
    """
    read seed coordinates
    """
   
    interface_voxels_left = pe.Node(interface=Function(input_names=["seed_file","use_sample"], output_names=["seed_list"], function=fetch_sample), name='70_interface_voxels_left')
    interface_voxels_left.inputs.use_sample = use_sample
    dmripipeline.connect(inputnode, "seeds_left", interface_voxels_left,"seed_file")
    
    interface_voxels_right = interface_voxels_left.clone(name='70_interface_voxels_right')
    dmripipeline.connect(inputnode, "seeds_right", interface_voxels_right,"seed_file")
    
    """
    Get the direct connectivity matrix
    """
        
    test_tracts = pe.Node(interface=Function(input_names=["tract_list_left", "tract_list_right","voxel_list_left","voxel_list_right","max_value"],
                                                        output_names=["exclusion_list"],
                                                        function=test_tracts), name='71_test_tracts')
    test_tracts.inputs.max_value = tract_number
    test_tracts.run_without_submitting = True
#    test_tracts.plugin_args={'override_specs': 'requirements = Machine == "kalifornien.cbs.mpg.de"'}
    dmripipeline.connect(inputnode, "tracts_left", test_tracts, "tract_list_left")
    dmripipeline.connect(inputnode, "tracts_right", test_tracts, "tract_list_right")
    dmripipeline.connect(interface_voxels_left, "seed_list", test_tracts, "voxel_list_left")
    dmripipeline.connect(interface_voxels_right, "seed_list", test_tracts, "voxel_list_right")
    
    tract_exclusion_mask = pe.Node(interface=Function(input_names=["voxel_list", "ref_image","outfile"], output_names=["outfile"], function=voxels2nii), name='72_tract_exclusion_mask')
    tract_exclusion_mask.inputs.outfile = subject_ID + '_tractseed_exclusion_mask.nii'
    dmripipeline.connect(inputnode, "wm", tract_exclusion_mask, "ref_image")
    dmripipeline.connect(test_tracts, "exclusion_list", tract_exclusion_mask, "voxel_list")
    
    


    """
    # invert and binarize tract exclusion mask and remove those voxels from the index interfaces
    """
    tract_denoise_mask = pe.Node(interface=fsl.maths.MathsCommand(), name='74_tract_denoise_mask')
    tract_denoise_mask.inputs.args = '-binv'
    tract_denoise_mask.run_without_submitting = True
    dmripipeline.connect(tract_exclusion_mask, "outfile", tract_denoise_mask, "in_file")
    
    index_pruned_left = pe.Node(interface=fsl.maths.ApplyMask(), name='75_interface_pruned_left')
    index_pruned_left.inputs.out_file = subject_ID + '_interface_pruned_left.nii'
    index_pruned_left.run_without_submitting = True
    dmripipeline.connect(inputnode, "index_left", index_pruned_left, "in_file")
    dmripipeline.connect(tract_denoise_mask, "out_file", index_pruned_left, "mask_file")
       
    index_pruned_right = index_pruned_left.clone(name='75_interface_pruned_right')
    index_pruned_right.inputs.out_file = subject_ID + '_interface_pruned_right.nii'
    dmripipeline.connect(inputnode, "index_right", index_pruned_right, "in_file")
    dmripipeline.connect(tract_denoise_mask, "out_file", index_pruned_right, "mask_file")
    
    interface_final_left = pe.Node(interface=Function(input_names=["interface_file","outfile_prefix"], output_names=["voxel_file","mm_file","mrtrix_file","voxel_list"], function=get_voxels), name='75b_interface_final_left')
    interface_final_left.inputs.outfile_prefix = subject_ID + '_interface_final_left'
    interface_final_left.run_without_submitting = True
    dmripipeline.connect([(index_pruned_left, interface_final_left, [("out_file", "interface_file")])])
    
    interface_final_right = interface_final_left.clone(name='75b_interface_final_right')
    interface_final_right.inputs.outfile_prefix = subject_ID + '_interface_final_right'
    dmripipeline.connect([(index_pruned_right, interface_final_right, [("out_file", "interface_file")])])
    
    tree_roi_left = pe.Node(interface=Function(input_names=["interface_file", "out_filename", "use_sample"], output_names=["out_file"], function=write_tree_roi), name='75c_tree_roi_left')
    tree_roi_left.inputs.out_filename = subject_ID + '_hclust_roi_left.txt'
    tree_roi_left.inputs.use_sample = use_sample
    tree_roi_left.run_without_submitting = True
    dmripipeline.connect(index_pruned_left,"out_file", tree_roi_left, "interface_file")

    
    tree_roi_right = tree_roi_left.clone(name='75c_tree_roi_right')
    tree_roi_right.inputs.out_filename = subject_ID + '_hclust_roi_right.txt'
    dmripipeline.connect(index_pruned_right,"out_file", tree_roi_right, "interface_file")

    """
    # warp index image to t1 space
    """
    index_warped_2_t1_left = pe.Node (interface=ants.WarpImageMultiTransform(), name='76_index_warped_2_t1_left')
    index_warped_2_t1_left.inputs.use_nearest = True
    index_warped_2_t1_left.run_without_submitting = True
    dmripipeline.connect([(index_pruned_left, index_warped_2_t1_left, [('out_file', 'input_image')])])
    dmripipeline.connect([(inputnode, index_warped_2_t1_left, [('fa', 'reference_image')])])
    dmripipeline.connect([(inputnode, index_warped_2_t1_left, [('warp', 'transformation_series')])])
    
    index_warped_2_t1_right = index_warped_2_t1_left.clone(name='76_index_warped_2_t1_right')
    dmripipeline.connect([(index_pruned_right, index_warped_2_t1_right, [('out_file', 'input_image')])])
    dmripipeline.connect([(inputnode, index_warped_2_t1_right, [('fa', 'reference_image')])])
    dmripipeline.connect([(inputnode, index_warped_2_t1_right, [('warp', 'transformation_series')])])
    
    index_final_2_t1_left = pe.Node(interface=fsl.ApplyXfm(), name='77_index_final_2_t1_left')
    index_final_2_t1_left.inputs.apply_xfm = True
    index_final_2_t1_left.run_without_submitting = True
    index_final_2_t1_left.inputs.interp = 'nearestneighbour'
    index_final_2_t1_left.inputs.out_file = subject_ID + '_index_seedt1_left.nii'
    dmripipeline.connect([(index_warped_2_t1_left, index_final_2_t1_left , [("output_image", "in_file")])])
    dmripipeline.connect([(inputnode, index_final_2_t1_left , [("inv_flirt_mat", "in_matrix_file")])])
    dmripipeline.connect([(inputnode, index_final_2_t1_left , [("t1", "reference")])])
    
    index_final_2_t1_right = index_final_2_t1_left.clone(name='77_index_final_2_t1_right')
    index_final_2_t1_right.inputs.out_file = subject_ID + '_index_seedt1_right.nii'
    dmripipeline.connect([(index_warped_2_t1_right, index_final_2_t1_right , [("output_image", "in_file")])])
    dmripipeline.connect([(inputnode, index_final_2_t1_right , [("inv_flirt_mat", "in_matrix_file")])])
    dmripipeline.connect([(inputnode, index_final_2_t1_right , [("t1", "reference")])])
    
    """
    extra processing
    """
    

    index_vol2surf_left = pe.Node(interface=fsurf.SampleToSurface(), name='78_index_vol2surf_left')
    index_vol2surf_left.inputs.hemi = 'lh'
    index_vol2surf_left.inputs.subject_id = subject_ID
    index_vol2surf_left.inputs.reg_header = True
    index_vol2surf_left.inputs.interp_method = 'nearest'
    index_vol2surf_left.inputs.sampling_method = 'point'
    index_vol2surf_left.inputs.sampling_range = 0  
    index_vol2surf_left.inputs.sampling_units = 'frac'   
    index_vol2surf_left.inputs.surface = 'orig'
    #index_vol2surf_left.inputs.cortex_mask = True
    index_vol2surf_left.inputs.terminal_output = 'file'
    index_vol2surf_left.inputs.out_file = subject_ID + '_index_seedt1_2surf_left.mgz'
    index_vol2surf_left.run_without_submitting = True
    dmripipeline.connect([(index_final_2_t1_left, index_vol2surf_left, [('out_file', 'source_file')])])
     
    index_vol2surf_right = index_vol2surf_left.clone(name='78_index_vol2surf_right')
    index_vol2surf_right.inputs.hemi = 'rh'
    index_vol2surf_right.inputs.out_file = subject_ID + '_index_seedt1_2surf_right.mgz'
    dmripipeline.connect([(index_final_2_t1_right, index_vol2surf_right, [('out_file', 'source_file')])])
    
    
    index_2_t1_reorient_left = pe.Node(interface=fsl.Reorient2Std(), name='79_next_2_t1_reorient_left')
    index_2_t1_reorient_left.inputs.out_file = subject_ID + '_index_seedt1_reorient_left.nii'
    index_2_t1_reorient_left.run_without_submitting = True
    dmripipeline.connect(index_final_2_t1_left, 'out_file', index_2_t1_reorient_left,  'in_file')
    
    index_2_t1_reorient_right = index_2_t1_reorient_left.clone(name='79_next_2_t1_reorient_right')
    index_2_t1_reorient_right.inputs.out_file = subject_ID + '_index_seedt1_reorient_right.nii'
    dmripipeline.connect(index_final_2_t1_right, 'out_file', index_2_t1_reorient_right,  'in_file')
    
    index_interface2surf_left = pe.Node(interface=Function(input_names=["interface_image", "surface_file","cortex_label","ref_mgz","out_file"], output_names=["out_file"],
                                                        function=interface2surf), name='80_index_interface2surf_left')
    index_interface2surf_left.inputs.surface_file = subjects_dir + '/' + subject_ID + '/surf/lh.orig'
    index_interface2surf_left.inputs.cortex_label = subjects_dir + '/' + subject_ID + '/label/lh.cortex.label'
    index_interface2surf_left.inputs.out_file = subject_ID + '_index_seedt1_2surf_left.mgz'
    dmripipeline.connect(index_2_t1_reorient_left, 'out_file', index_interface2surf_left,  'interface_image')
    dmripipeline.connect(index_vol2surf_left, 'out_file', index_interface2surf_left,  'ref_mgz')
    
    index_interface2surf_right = index_interface2surf_left.clone(name='80_index_interface2surf_right')
    index_interface2surf_right.inputs.surface_file = subjects_dir + '/' + subject_ID + '/surf/rh.orig'
    index_interface2surf_right.inputs.cortex_label = subjects_dir + '/' + subject_ID + '/label/rh.cortex.label'
    index_interface2surf_right.inputs.out_file = subject_ID + '_index_seedt1_2surf_right.mgz'
    dmripipeline.connect(index_2_t1_reorient_right, 'out_file', index_interface2surf_right,  'interface_image')
    dmripipeline.connect(index_vol2surf_right, 'out_file', index_interface2surf_right,  'ref_mgz')
    
    
    fs_indexlist_left = pe.Node(interface=Function(input_names=["in_surface_values","cortex_label","out_file"], output_names=["out_file"], function=surf2file), name='81_index_fsnative_left')
    fs_indexlist_left.inputs.cortex_label = op.join(freesurfer_dir, subject_ID+'/label/lh.cortex.label')
    fs_indexlist_left.inputs.out_file = subject_ID + '_seed_index_fsnative_left.txt'
    fs_indexlist_left.run_without_submitting = True
    dmripipeline.connect([(index_interface2surf_left, fs_indexlist_left, [("out_file", "in_surface_values")])])
    
    fs_indexlist_right = fs_indexlist_left.clone(name='81_index_fsnative_right')
    fs_indexlist_right.inputs.cortex_label = op.join(freesurfer_dir,subject_ID+'/label/rh.cortex.label')
    fs_indexlist_right.inputs.out_file = subject_ID + '_seed_index_fsnative_right.txt'
    dmripipeline.connect([(index_interface2surf_right, fs_indexlist_right, [("out_file", "in_surface_values")])])
    
    """""""""""""""""""""""""""
    """""""""""""""""""""""""""
    
    index_fsaverage5_left = pe.Node(interface=fsurf.SurfaceTransform(), name='81_index_fsaverage5_left')
    index_fsaverage5_left.inputs.hemi = 'lh'
    index_fsaverage5_left.inputs.source_subject = subject_ID
    index_fsaverage5_left.inputs.target_subject = 'fsaverage5'
    index_fsaverage5_left.inputs.args = '--mapmethod nnf --label-src lh.cortex.label --label-trg lh.cortex.label'
    index_fsaverage5_left.inputs.out_file = subject_ID + '_index_seedt1_fsaverage5_left.mgz'
    #index_fsaverage5_left.run_without_submitting = True
    dmripipeline.connect([(index_interface2surf_left, index_fsaverage5_left, [('out_file', 'source_file')])])
    
    index_fsaverage5_right = index_fsaverage5_left.clone(name='81_index_fsaverage5_right')
    index_fsaverage5_right.inputs.hemi = 'rh'
    index_fsaverage5_left.inputs.args = '--mapmethod nnf --label-src rh.cortex.label --label-trg rh.cortex.label'
    index_fsaverage5_right.inputs.out_file = subject_ID + '_index_seedt1_fsaverage5_right.mgz'
    dmripipeline.connect([(index_interface2surf_right, index_fsaverage5_right, [('out_file', 'source_file')])])
    
    fs5_indexlist_left = pe.Node(interface=Function(input_names=["in_surface_values","cortex_label","out_file"], output_names=["out_file"], function=surf2file), name='82_index_fsav5_left')
    fs5_indexlist_left.inputs.cortex_label = op.join(freesurfer_dir,'fsaverage5/label/lh.cortex.label')
    fs5_indexlist_left.inputs.out_file = subject_ID + '_seed_index_fs5_left.txt'
    #fs5_indexlist_left.run_without_submitting = True
    dmripipeline.connect([(index_fsaverage5_left, fs5_indexlist_left, [("out_file", "in_surface_values")])])
    
    fs5_indexlist_right = fs5_indexlist_left.clone(name='82_index_fsav5_right')
    fs5_indexlist_right.inputs.cortex_label = op.join(freesurfer_dir,'fsaverage5/label/rh.cortex.label')
    fs5_indexlist_right.inputs.out_file = subject_ID + '_seed_index_fs5_right.txt'
    dmripipeline.connect([(index_fsaverage5_right, fs5_indexlist_right, [("out_file", "in_surface_values")])])
    
    
    index_fsaverage4_left = pe.Node(interface=fsurf.SurfaceTransform(), name='81_index_fsaverage4_left')
    index_fsaverage4_left.inputs.hemi = 'lh'
    index_fsaverage4_left.inputs.source_subject = subject_ID
    index_fsaverage4_left.inputs.target_subject = 'fsaverage4'
    index_fsaverage4_left.inputs.args = '--mapmethod nnf --label-src lh.cortex.label --label-trg lh.cortex.label'
    index_fsaverage4_left.inputs.out_file = subject_ID + '_index_seedt1_fsaverage4_left.mgz'
    #index_fsaverage4_left.run_without_submitting = True
    dmripipeline.connect([(index_interface2surf_left, index_fsaverage4_left, [('out_file', 'source_file')])])
    
    index_fsaverage4_right = index_fsaverage4_left.clone(name='81_index_fsaverage4_right')
    index_fsaverage4_right.inputs.hemi = 'rh'
    index_fsaverage4_left.inputs.args = '--mapmethod nnf --label-src rh.cortex.label --label-trg rh.cortex.label'
    index_fsaverage4_right.inputs.out_file = subject_ID + '_index_seedt1_fsaverage4_right.mgz'
    dmripipeline.connect([(index_interface2surf_right, index_fsaverage4_right, [('out_file', 'source_file')])])
    
    fs4_indexlist_left = pe.Node(interface=Function(input_names=["in_surface_values","cortex_label","out_file"], output_names=["out_file"], function=surf2file), name='82_index_fsav4_left')
    fs4_indexlist_left.inputs.cortex_label = op.join(freesurfer_dir,'fsaverage4/label/lh.cortex.label')
    fs4_indexlist_left.inputs.out_file = subject_ID + '_seed_index_fs4_left.txt'
    #fs4_indexlist_left.run_without_submitting = True
    dmripipeline.connect([(index_fsaverage4_left, fs4_indexlist_left, [("out_file", "in_surface_values")])])
    
    fs4_indexlist_right = fs4_indexlist_left.clone(name='82_index_fsav4_right')
    fs4_indexlist_right.inputs.cortex_label = op.join(freesurfer_dir,'fsaverage4/label/rh.cortex.label')
    fs4_indexlist_right.inputs.out_file = subject_ID + '_seed_index_fs4_right.txt'
    dmripipeline.connect([(index_fsaverage4_right, fs4_indexlist_right, [("out_file", "in_surface_values")])])
    
    

    """
    use a sink to save outputs
    """
    
    datasink = pe.Node(io.DataSink(), name='99_datasink')
    datasink.inputs.base_directory = output_dir
    datasink.inputs.container = subject_ID
    datasink.inputs.parameterization = True
    #datasink.run_without_submitting = True

    dmripipeline.connect(index_pruned_left, 'out_file', datasink, 'interface_index'+postfix+'.@3')
    dmripipeline.connect(index_pruned_right, 'out_file', datasink, 'interface_index'+postfix+'.@4')
    
    dmripipeline.connect(interface_final_left, 'voxel_file', datasink, 'roi.@10')
    dmripipeline.connect(interface_final_left, 'mm_file', datasink, 'roi.@11')
    dmripipeline.connect(interface_final_right, 'voxel_file', datasink, 'roi.@13')
    dmripipeline.connect(interface_final_right, 'mm_file', datasink, 'roi.@14')
    dmripipeline.connect(tree_roi_left, 'out_file', datasink, 'roi.@15')
    dmripipeline.connect(tree_roi_right, 'out_file', datasink, 'roi.@16')

    
    
    dmripipeline.connect(index_final_2_t1_left, 'out_file', datasink, 'interface_index'+postfix+'.@5')
    dmripipeline.connect(index_final_2_t1_right, 'out_file', datasink, 'interface_index'+postfix+'.@6')
    dmripipeline.connect(index_interface2surf_left, 'out_file', datasink, 'interface_index'+postfix+'.@7')
    dmripipeline.connect(index_interface2surf_right, 'out_file', datasink, 'interface_index'+postfix+'.@8')
    dmripipeline.connect(index_fsaverage5_left, 'out_file', datasink, 'interface_index'+postfix+'.@9')
    dmripipeline.connect(index_fsaverage5_right, 'out_file', datasink, 'interface_index'+postfix+'.@10')
    dmripipeline.connect(fs5_indexlist_left, 'out_file', datasink, 'interface_index'+postfix+'.@11')
    dmripipeline.connect(fs5_indexlist_right, 'out_file', datasink, 'interface_index'+postfix+'.@12') 
    dmripipeline.connect(index_fsaverage4_left, 'out_file', datasink, 'interface_index'+postfix+'.@13')
    dmripipeline.connect(index_fsaverage4_right, 'out_file', datasink, 'interface_index'+postfix+'.@14')
    dmripipeline.connect(fs4_indexlist_left, 'out_file', datasink, 'interface_index'+postfix+'.@15')
    dmripipeline.connect(fs4_indexlist_right, 'out_file', datasink, 'interface_index'+postfix+'.@16')
    dmripipeline.connect(fs_indexlist_left, 'out_file', datasink, 'interface_index'+postfix+'.@17')
    dmripipeline.connect(fs_indexlist_right, 'out_file', datasink, 'interface_index'+postfix+'.@18')
    dmripipeline.connect(tract_exclusion_mask, 'outfile', datasink, 'interface_index'+postfix+'.@19')
   


    
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    ===============================================================================
    Connecting the workflow
    ===============================================================================
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    
    """
    Create a higher-level workflow
    ------------------------------
    Finally, we create another higher-level workflow to connect our dmripipeline workflow with the info and datagrabbing nodes
    declared at the beginning. Our tutorial is now extensible to any arbitrary number of subjects by simply adding
    their names to the subject list and their data to the proper folders.
    """ 
    
    connectprepro = pe.Workflow(name="p4_postpro")
    
    connectprepro.base_dir = op.abspath(workflow_dir+ "/workflow_"+subject_ID)
    connectprepro.connect([(datasource, dmripipeline, [('wm', 'inputnode.wm'),('seeds_left', 'inputnode.seeds_left'),('seeds_right', 'inputnode.seeds_right'),
                                                       ('t1', 'inputnode.t1'),('warp', 'inputnode.warp'),('inv_flirt_mat', 'inputnode.inv_flirt_mat'),
                                                       ('fa', 'inputnode.fa'),('index_left', 'inputnode.index_left'),('index_right', 'inputnode.index_right')]),
                           (tracts_left_source, dmripipeline, [('tracts_left', 'inputnode.tracts_left')]),
                           (tracts_right_source, dmripipeline, [('tracts_right', 'inputnode.tracts_right')])])
    
    return connectprepro
