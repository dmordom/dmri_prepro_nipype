# dmri_prepro_nipype
dMRI data preprocessing and single seed voxel tracking pipeline

#### Related Publications:

Moreno-Dominguez, D., Watanabe, A., Gorgolewski, K. J., Schäfer, A., Goulas, A., Kipping, J., Kanaan, A. S., Anwander, A., Toro, R., & Margulies, D. S. (2014). Multi-modal parcellation of the frontal lobe. Poster presented at 20th Annual Meeting of the Organization for Human Brain Mapping (OHBM), Hamburg, Germany.

http://pubman.mpdl.mpg.de/pubman/item/escidoc:2039365:4/component/escidoc:2039364/Moreno-Dominguez_OHBM2014.pdf

#### Usage:

This pipeline accepts an input folder with the following scan files:
t1.nii.gz (the t1 image)
data.nii.gz (the dmri data)
bvecs (the scan directions)
bvals (the b values)

And performs preprocesing in order to obtain freesurfer surfaces, quality white matter masks and gm/wm interface, single seed voxel tractography and projection from seed voxels to freesurfer surface points.

Requirements before running:

Install if necessary the following packages:
FSL
ANTS
FREESURFER
MRTRIX
PYTHON
NIPYPE (FOR PYTHON)
A CONDOR SYSTEM FOR CLUSTER COMPUTING

================================================================

Once all dependencies are installed open a console and console run:

"FSL --version 5.0"
"export PATH=/your_ants_path/ANTS/antsbin/bin:$PATH"
"MRTRIX"
"Freesurfer"
"SUBJECT_DIR=your_freesurfer_subjects_dir"
"python p0_main.py"  (from the folder where you cloned/copied these tools to)
The pipeline will start running

================================================================

Some variables can and must be tuned in p0_main.py:

    tract_number = the number of streamlines that are wished to be generated per seed voxel
    tract_step = the tracking step size
    freesurfer_dir = the directory where the freesurfer recon_all outputs will be written (or are located)
    data_dir = the input data directory
    
    register_to_mni = If true the t1 data will be registered to an mni template before generating the surfaces (but then dmri data projection will not work unless dmri data is also registered )
    use_condor = use cluster computing
    use_sample= generate only a small sample of tracts from the gm/wm boundary
    clean = eliminate workflow intermediate outputs after a sucessful run
    pipe_start = pipe script point where to start processing the first subject
    pipe_stop = pipe script point where to stop processing each subject
    pipe_restart= pipe script point where to start processing the next subject
    
                    
    subject_list = a list with the names of all subjects to be processed as per the input folders


    if (use_sample):
        workflow_dir = directory for the sample option workflow
        output_dir = directory for the sample option outputs
        chunk_nr = number of chunks into which to divide the tractography computing for the sample option
    else:
        workflow_dir = directory for the workflow intermediate outputs
        output_dir = directory for the outputs
        chunk_nr = number of chunks into which to divide the tractography computing 


================================================================

REMEMBER:

 - generate the output directory and workflow dirs before running
 - copy the track_script_header.sh and track_script_body.sh files to the output directory before running
