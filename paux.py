'''
Created on Oct 17, 2013

@author: moreno
'''



def get_image_centre(image_data):
    import numpy as np
    image_shape=np.shape(image_data)
    dx=image_shape[0]
    dy=image_shape[1]
    dz=image_shape[2]
    
    min_x=dx
    max_x=0
    min_y=dy
    max_y=0
    min_z=dz
    max_z=0
    
    for x in xrange(dx):
        for y in xrange(dy):
            for z in xrange(dz):
                if image_data[x][y][z] > 0:
                    if x < min_x:
                        min_x = x
                    if x > max_x:
                        max_x = x
                    if y < min_y:
                        min_y = y
                    if y > max_y:
                        max_y = y
                    if z < min_z:
                        min_z = z
                    if z > max_z:
                        max_z = z
        
    x_centre = int((min_x + max_x) / 2)
    y_centre = int((min_y + max_y) / 2)
    z_centre = int((min_z + max_z) / 2)
    centre=np.array([x_centre, y_centre, z_centre])
    return np.copy(centre)

def generate_lateral_line(image_file,out_filename = 'lateral_line.nii'):
    import os
    import numpy as np
    import nibabel as nb
    from paux import get_image_centre as gc
    image=nb.load(image_file)
    image_data=image.get_data()
    
    centre=gc(image_data)
    y_centre=centre[1]
    z_centre=centre[2]
    lateral_line=np.zeros_like(image_data,dtype=np.uint8)
    
    dx=(np.shape(lateral_line))[0]
    
    for x in xrange(dx):
        lateral_line[x][y_centre][z_centre] = 255
                    
    lateral_line_image = nb.Nifti1Image(lateral_line, image.get_affine(), image.get_header())
    nb.save(lateral_line_image, out_filename)    
    return os.path.abspath(out_filename)


def aff2rigid(in_mat,out_mat):
       
    import numpy as np
    import os

    # Load in the necessary info
    a=np.loadtxt(in_mat)
    # set specific AC and PC coordinates in FLIRT convention (x1=AC, x2=PC, x3=point above x1 in the mid-sag plane)
    x1=np.matrix([[91],[129],[67],[1]])
    x2=np.matrix([[91],[100],[70],[1]])
    x3=np.matrix([[91],[129],[117],[1]])
    
    ainv=np.linalg.inv(a)
    
    # vectors v are in MNI space, vectors w are in native space
    v21=(x2-x1)
    v31=(x3-x1)
    # normalise and force orthogonality
    v21=v21/np.linalg.norm(v21)
    v31=v31-np.multiply(v31.T * v21,v21)
    v31=v31/np.linalg.norm(v31)
    tmp=np.cross(v21[0:3,0].T,v31[0:3,0].T).T
    v41=np.mat(np.zeros((4,1)))
    v41[0:3,0]=tmp
    # Map vectors to native space
    w21=ainv*(v21)
    w31=ainv*(v31)
    # normalise and force orthogonality
    w21=w21/np.linalg.norm(w21)
    w31=w31-np.multiply(w31.T * w21,w21)
    w31=w31/np.linalg.norm(w31)
    tmp=np.cross(w21[0:3,0].T,w31[0:3,0].T).T
    w41=np.mat(np.zeros((4,1)))
    w41[0:3,0]=tmp
    
    # setup matrix: native to MNI space
    r1=np.matrix(np.eye(4))
    r1[0:4,0]=w21
    r1[0:4,1]=w31
    r1[0:4,2]=w41
    r2=np.matrix(np.eye(4))
    r2[0,0:4]=v21.T
    r2[1,0:4]=v31.T
    r2[2,0:4]=v41.T
    r=r2.T*r1.T
    
    # Fix the translation (keep AC=x1 in the same place)
    ACmni=x1
    ACnat=ainv*x1
    trans=ACmni-r*ACnat
    r[0:3,3]=trans[0:3]
    
    # Save out the result
    np.savetxt(out_mat,r,fmt='%14.10f')
    return os.path.abspath(out_mat)


"""
threshold b values in bval file lower than thr to 0
"""
def threshold_bval(in_file, thr):
    import os
    import numpy as np
    value = np.genfromtxt(in_file)
    value[value < thr] = 0
    out_file = 'thresholded_%s.bval' % thr
    np.savetxt(out_file, value, delimiter=' ')
    return os.path.abspath(out_file)

"""
tget mean b0 from dwi image and bvals
"""
def get_mean_b0(bvals_file,dwi_file,out_filename):
    import os
    import numpy as np
    import nibabel as nb
    bvals = np.loadtxt(bvals_file, delimiter=' ')
    dwi_img=nb.load(dwi_file)
    dwi_data=dwi_img.get_data()
    
    sum_b0 = np.zeros(dwi_data[:,:,:,0].shape)
    num_b0=0
    
    for i in xrange(len(bvals)):
        if (bvals[i]==0):
            sum_b0=np.add(sum_b0,dwi_data[:,:,:,i])
            num_b0 += 1
            
    mean_b0=np.true_divide(sum_b0,num_b0)
    mean_b0_image = nb.Nifti1Image(mean_b0, dwi_img.get_affine(), dwi_img.get_header())
    nb.save(mean_b0_image, out_filename)    
    return os.path.abspath(out_filename)


"""
define which ribbon to pick... lh.ribbon.mgz, rh.ribbon.mgz or ribbon.mgz
"""
def pick_full_ribbon(ribbon_list):
    for f in ribbon_list:
        if f.endswith('lh.ribbon.mgz') or f.endswith('rh.ribbon.mgz'):
            continue
        else:
            return f


"""
Get the voxel coordinates from the file, and transfrom them to mm coordinates for mrtrix
text fiels with the coordinates are saved.
Also, the voxels are ordered by z,y,x. that is, all the voxels in one slice are contigous
"""
def get_voxels(interface_file,outfile_prefix):
    import numpy as np
    import nibabel
    import os
    interfaceFile = nibabel.load(interface_file)
    v = np.array(interfaceFile.get_data())
    voxelCoordList = []

    for x, y, z in zip(*np.nonzero(v)):
        voxelCoord = [x,y,z]
        voxelCoordList.append(voxelCoord)
        
    voxelCoordList.sort(key=lambda tup: tup[1])
    voxelCoordList.sort(key=lambda tup: tup[2])
    mmCoordList = []
    mmOutputList = []
    radius = 1.0
    affineMatrix = interfaceFile.get_affine()
    
    for x, y, z in voxelCoordList:
        voxelCoord = [x,y,z]
        mmCoordVector = nibabel.affines.apply_affine(affineMatrix, voxelCoord)
        mmCoord = list(mmCoordVector)
        mmCoordList.append(mmCoord)
        mmCoordOutput=list(mmCoordVector)
        mmCoordOutput.append(radius)
        mmOutputList.append(mmCoordOutput)
     
    voxel_file = outfile_prefix + '_voxels.txt'
    np.savetxt(voxel_file, voxelCoordList, fmt='%d', delimiter=' ')
    mm_file = outfile_prefix + '_mm.txt'
    np.savetxt(mm_file, mmCoordList, fmt='%f', delimiter=' ')
    mrtrix_file = outfile_prefix + '_mrtrix.txt'
    np.savetxt(mrtrix_file, mmOutputList, fmt='%f', delimiter=' ')

    return os.path.abspath(voxel_file), os.path.abspath(mm_file), os.path.abspath(mrtrix_file), voxelCoordList

"""
writes seed voxels in a format to be read by the tree building tool
"""
def write_tree_roi(interface_file, out_filename, use_sample=False):
    import os
    import numpy as np
    import nibabel as nb
    from paux import image_dims

    sampleSize = 500

    interfaceFile = nb.load(interface_file)
    data = np.array(interfaceFile.get_data())
    voxelCoordList = []

    for x, y, z in zip(*np.nonzero(data)):
        voxelCoord = [x,y,z]
        voxelCoordList.append(voxelCoord)
        
    voxelCoordList.sort(key=lambda tup: tup[1])
    voxelCoordList.sort(key=lambda tup: tup[2])
    indexList = []
    
    for coord in voxelCoordList:
        index = int(data[coord[0],coord[1],coord[2]]) - 1
        indexList.append(index)
        
    finalIndexList = []
    finalCoordList = []
    if( use_sample ):
        for i in xrange(len(indexList)):
            if indexList[i] < sampleSize:
                finalIndexList.append(indexList[i])
                finalCoordList.append(voxelCoordList[i])
    else:
        finalIndexList = indexList
        finalCoordList = voxelCoordList
            
    dimensions = image_dims(interface_file)
    
    with open(out_filename, 'w+') as roi_file:
        roi_file.write("#imagesize\n")
        roi_file.write(str(dimensions[0])+" "+str(dimensions[1])+" "+str(dimensions[2])+" nifti\n")
        roi_file.write("#endimagesize\n\n")
        roi_file.write("#trackindex\n")
        for index in finalIndexList:
            roi_file.write(str(index)+"\n")
        roi_file.write("#endtrackindex\n\n")
        roi_file.write("#roi\n")
        for coord in finalCoordList:
            roi_file.write(str(coord[0])+" "+str(coord[1])+" "+str(coord[2])+"\n")
        roi_file.write("#endroi\n")

    return os.path.abspath(out_filename)

"""
Read a txt files with voxel coordinates and return it as a lost of lists
"""
def fetch_sample(seed_file, use_sample=False):
    import numpy as np
    
    sampleSize = 500

    seed_list = np.loadtxt(seed_file, delimiter=' ')
    
#     seeds_shape = np.shape(seed_list)
#     sample_seeds = np.zeros((9,seeds_shape[1]))
#     sample_seeds[0] = seed_list[2000]
#     sample_seeds[1] = seed_list[2001]
#     sample_seeds[2] = seed_list[2002]
#     sample_seeds[3] = seed_list[3500]
#     sample_seeds[4] = seed_list[3501]
#     sample_seeds[5] = seed_list[3502]
#     sample_seeds[6] = seed_list[5000]
#     sample_seeds[7] = seed_list[5001]
#     sample_seeds[8] = seed_list[5002]
    
    seeds_shape = np.shape(seed_list)
    sample_seeds = np.zeros((sampleSize,seeds_shape[1]))
    for i in xrange(sampleSize):
        sample_seeds[i] = seed_list[i]


    if(use_sample):
        seed_list = sample_seeds.tolist()
    else:
        seed_list = seed_list.tolist()

    return seed_list




"""
assign an id index to every voxel in the mask
"""
def assign_voxel_ids(in_seed_file,seedvoxel_list,outfile_prefix):
    import os
    import nibabel
    mask_nii = nibabel.load(in_seed_file)
    data = mask_nii.get_data()
    voxel_count = 0;
    index_list = []
    
    for x, y, z in seedvoxel_list:
        voxel_count += 1
        data[x,y,z]=voxel_count
        index_list.append(voxel_count)
                         
    index_image = nibabel.Nifti1Image(data, mask_nii.get_affine(), mask_nii.get_header())
    out_index_file = outfile_prefix +'_index.nii'
    nibabel.save(index_image, out_index_file)
    return os.path.abspath(out_index_file), index_list


"""
generate a numbered list of files
"""
def get_outfile_list(infile_list,outfile_prefix='probtract',extension='nii'):
    
    listlength = len(infile_list) 
    outfile_list=['']*listlength
    
    for i in xrange(listlength):
        number = '_%06d.' % i
        outfile_list[i]= outfile_prefix + number + extension 
    
    return outfile_list


"""
convert a voxel list into a nifti mask
"""
def voxels2nii(voxel_list, ref_image, outfile):
    import os
    import nibabel
    import numpy as np
    ref_nii = nibabel.load(ref_image)
    ref_data = ref_nii.get_data()

    exclusion_data = np.zeros( np.shape(ref_data) )
    
    for x, y, z in voxel_list:
        exclusion_data[x,y,z]=1
                         
    exclusion_image = nibabel.Nifti1Image(exclusion_data, ref_nii.get_affine(), ref_nii.get_header())
    nibabel.save(exclusion_image, outfile)
    return os.path.abspath(outfile)




"""
read a list of visitation maps and create a direct connectivity matrix
"""
def get_connectivity_matrix(tract_list_left, tract_list_right, voxel_list_left, voxel_list_right, max_value):
    
    def get_connectivity_submatrix(tract_list,this_voxel_list,opposite_voxel_list,max_value):
        
        def get_seed_connectivities(in_seed_tract,seedvoxel_list):
            import nibabel
            import numpy as np
                        
            tract_nii = nibabel.load(in_seed_tract)
            
            data = tract_nii.get_data()
            out_seed_connectivities=np.zeros(len(seedvoxel_list))
            index=0
            
            for x, y, z in seedvoxel_list:
                out_seed_connectivities[index]=data[x,y,z]
                index += 1
                                 
            return out_seed_connectivities
        
        import numpy as np
        from scipy.sparse import csr_matrix
        
        seed_dim_this=len(this_voxel_list)
        seed_dim_opposite=len(opposite_voxel_list)
        tract_dim=len(tract_list)
        
        zeroline_this = np.zeros((1,seed_dim_this))
        zeroline_opposite = np.zeros((1,seed_dim_opposite))
        
        exclusion_list = []
        exclusion_indexes = []
                
        submatrix_this=np.zeros((tract_dim,seed_dim_this))
        for i in xrange(tract_dim):
            submatrix_this[i]=get_seed_connectivities(tract_list[i],this_voxel_list)
        # check if diagonal elements are lower than 5000, if so, set to 0
        for i in xrange(seed_dim_this):
            if( submatrix_this[i,i] < max_value ):
                submatrix_this[i] = zeroline_this
                exclusion_indexes.append(i)
                exclusion_list.append(this_voxel_list[i])

        sparse_this = csr_matrix(submatrix_this)
        del(submatrix_this)
                           
        submatrix_opposite=np.zeros((tract_dim,seed_dim_opposite))
        for i in xrange(tract_dim):
            submatrix_opposite[i]=get_seed_connectivities(tract_list[i],opposite_voxel_list)
            
        for i in exclusion_indexes:
            submatrix_opposite[i] = zeroline_opposite
            
        sparse_opposite = csr_matrix(submatrix_opposite)
        del(submatrix_opposite)
                        
        return sparse_this, sparse_opposite, exclusion_list
            
    submatrix_left_left, submatrix_left_right, exclusion_left= get_connectivity_submatrix(tract_list_left, voxel_list_left, voxel_list_right, max_value)
    
    submatrix_right_right, submatrix_right_left, exclusion_right = get_connectivity_submatrix(tract_list_right, voxel_list_right, voxel_list_left, max_value)
    
    exclusion_list = []
    exclusion_list.extend(exclusion_left)
    exclusion_list.extend(exclusion_right)

    return submatrix_left_left, submatrix_left_right, submatrix_right_left, submatrix_right_right, exclusion_list


"""
test if the tracts managed to generate the total amount of streamlines
"""
def test_tracts(tract_list_left, tract_list_right, voxel_list_left, voxel_list_right, max_value):
    
    def test_subset(tract_list,this_voxel_list,max_value):
        
        def get_seed_max(in_seed_tract,seed_voxel):
            import nibabel as nb
            data = nb.load(in_seed_tract).get_data()
            return data[seed_voxel[0],seed_voxel[1],seed_voxel[2]]
        
        import numpy as np
        
        seed_dim_this=len(this_voxel_list)
        tract_dim=len(tract_list)
        
        assert seed_dim_this == tract_dim, "voxel list and tract list dimensions dont match"
        


        exclusion_list = []

        for i in xrange(seed_dim_this):
            if( get_seed_max(tract_list[i],this_voxel_list[i]) < max_value ):
                exclusion_list.append(this_voxel_list[i])
        
        return exclusion_list
            
    exclusion_left= test_subset(tract_list_left, voxel_list_left, max_value)
    exclusion_right = test_subset(tract_list_right, voxel_list_right, max_value)
    
    exclusion_list = []
    exclusion_list.extend(exclusion_left)
    exclusion_list.extend(exclusion_right)

    return exclusion_list



"""
gets a connectivity matrix as array, normalizes (with or without log) and saves in a mat file
"""
def normalize_matrix(in_array, max_value, outfile_prefix):
    
    import numpy as np
    import os.path as op
    import nibabel as nb
    from scipy.io import savemat
    
    #array with normalized values
    nat_array = np.array(in_array.todense())
    nat_array = nat_array / max_value;
    
    niiheader = nb.nifti1.Nifti1Header()
    niiaffine = np.identity(4)

#     nat_array = in_array / max_value;
    array_name_nat = outfile_prefix + '_nat'
    savemat(array_name_nat, {'obj0' : nat_array})
    nifti_image_nat = nb.Nifti1Image(nat_array, niiaffine, niiheader)
    nb.save(nifti_image_nat, array_name_nat + '.nii')
    del(nifti_image_nat)
    del(nat_array)

    #array with log-normalized values
    log_array = np.array(in_array.todense())
    log_array = np.log10(log_array)
#     log_array = np.log10(in_array)
    log_array[np.isinf(log_array)] = 0
    log_array = log_array / np.log10(max_value)
    array_name_log = outfile_prefix + '_log'
    savemat(array_name_log, { 'obj0': log_array})
    nifti_image_log = nb.Nifti1Image(log_array, niiaffine, niiheader)
    nb.save(nifti_image_log, array_name_log + '.nii')
    del(nifti_image_log)
    del(log_array)

    return op.abspath(array_name_nat+'.mat'), op.abspath(array_name_log+'.mat'), op.abspath(array_name_nat+'.nii'), op.abspath(array_name_log+'.nii')




"""
convert a surface volume in freesurfer to a an ascii list 
"""
def surf2file(in_surface_values, cortex_label, out_file):
    import os
    import nibabel
    import numpy as np
    seed_surface = nibabel.load(in_surface_values)
    surfindex_array = seed_surface.get_data()
    label_indices = np.loadtxt(cortex_label, delimiter=' ', dtype=long, skiprows=2, usecols=[0])
    final_array=np.zeros(len(surfindex_array))
    for i in label_indices:
        final_array[i]=surfindex_array[i]
    np.savetxt(out_file, final_array, fmt='%d', delimiter=' ')
    return os.path.abspath(out_file)

def image_dims(image_filename):
    import nibabel as nb
    import numpy as np
    
    image = nb.load(image_filename)
    image_data = image.get_data()
    image_shape = np.shape(image_data)
    return np.copy(image_shape)

def interface2surf(interface_image, surface_file, cortex_label, ref_mgz, out_file):

    import os
    import nibabel as nb
    import nibabel.freesurfer as nbfs
    import numpy as np
    import scipy.spatial.distance as syd
    
    # get image properties
    interfaceImage = nb.load(interface_image)
    interface_indexes = interfaceImage.get_data()
    interface_shape = np.shape(interface_indexes)
    reoriented_indexes = np.zeros(interface_shape)
    affineMatrix = interfaceImage.get_affine()
    
    # get surface and put it in voxel space
    surface = nbfs.read_geometry(surface_file)
    surface_coords = surface[0]
    surface_coords[:,0] = surface_coords[:,0] + (interface_shape[0]/2)
    surface_coords[:,1] = surface_coords[:,1] + (interface_shape[1]/2)
    surface_coords[:,2] = surface_coords[:,2] + (interface_shape[2]/2)
    surf_array_dim = np.shape(surface_coords)
    surf_length = surf_array_dim[0]
    label_indices = np.loadtxt(cortex_label, delimiter=' ', dtype=long, skiprows=2, usecols=[0])
    projected_index=np.zeros(surf_length)
    projected_distance=np.zeros(surf_length)-1
    
    # get interface coordinates and put them in normal voxel space
    voxelCoordList=[]
    for x, y, z in zip(*np.nonzero(interface_indexes)):
        voxelCoord = [x,y,z]
        if(affineMatrix[0,0]==-1):
            voxelCoord[0]=interface_shape[0]-1-voxelCoord[0]
        if(affineMatrix[1,1]==-1):
            voxelCoord[1]=interface_shape[1]-1-voxelCoord[1]
        if(affineMatrix[2,2]==-1):
            voxelCoord[2]=interface_shape[2]-1-voxelCoord[2]
        voxelCoordList.append(voxelCoord)
        reoriented_indexes[voxelCoord[0],voxelCoord[1],voxelCoord[2]]=interface_indexes[x,y,z]
    interface_voxels = np.array(voxelCoordList)
           

            
    for i in label_indices:
    
        surf_coord = surface_coords[i:i+1,:]
        surf_floor = np.floor(surf_coord)
        local_index = reoriented_indexes[surf_floor[0,0],surf_floor[0,1],surf_floor[0,2]]
        
        """
        -if the vertex lays in an index voxel assign directly
        -TO IMPLEMENT IF SLOW: check next in the 26-neighborhood
        -otherwise, check distances to all index voxels and choose smallest
        """
        
        if( local_index != 0):
            projected_index[i] = local_index
            projected_distance[i] = 0.0
        else: 
            all_dists = syd.cdist(surf_coord, interface_voxels + 0.5, 'euclidean')
            nearest_voxel_ID = np.argmin(all_dists)
            nearest_dist = all_dists[0,nearest_voxel_ID]
            projected_distance[i] = nearest_dist
            projected_voxel_coords=interface_voxels[nearest_voxel_ID,:]
            projected_index[i] = reoriented_indexes[ projected_voxel_coords[0],projected_voxel_coords[1],projected_voxel_coords[2] ]

    """
    convert projected_index into a .mif file
    """
    ref_mgz_file = nb.load(ref_mgz)    
    data=ref_mgz_file.get_data()
    data[:,0,0]=projected_index
    surface_projected_image = nb.MGHImage(data, ref_mgz_file.get_affine(), ref_mgz_file.get_header())
    nb.save(surface_projected_image, out_file)

    return os.path.abspath(out_file)


"""
writes a number sequence file with as may lines as input files 
"""
def write_sequence_file(file_list,out_file):
    import numpy as np
    import os

    list_size = len(file_list)
    out_array=np.zeros(list_size)

    for i in xrange(list_size):
        out_array[i]=i
        
    np.savetxt(out_file, out_array, fmt='%d', delimiter=' ')

    return os.path.abspath(out_file)




"""
downsamples and reorders matrix to the entries indicated by an index file 
"""

def downsample_matrix(index_row_file, index_col_file, matrix_file, out_prefix, dist2sim=True, transpose=False ):

    import numpy as np
    import os.path as op
    import nibabel as nb
    from scipy.io import savemat
    from scipy.io import loadmat
    import sys
    
    row_indices = np.loadtxt(index_row_file, dtype=long)
    col_indices = np.loadtxt(index_col_file, dtype=long)

    d_row=len(row_indices)
    d_col=len(col_indices)
    
    print "indices row: ", d_row, ". indices col ", d_col
    print "max row: ", max(row_indices), ". max col ", max(col_indices)

    matrix_struct = loadmat(matrix_file)
    
    if(transpose):
        dist_matrix=np.transpose(matrix_struct['obj0'])
    else:
        dist_matrix=matrix_struct['obj0']

    print "matrix shape: ", np.shape(dist_matrix), ". first 5x5: "
    print dist_matrix[0:5,0:5]
    
    sim_matrix = np.zeros((d_row,d_col))
    
    sys.stdout.flush()
    
    for i in xrange(d_row):
        if(row_indices[i]==0):
            sim_matrix[i] = np.zeros((1,d_col))
        else:
            for j in xrange(d_col):
                if(col_indices[j]==0):
                    sim_matrix[i,j]=0
                else:
                    if(dist2sim):
                        sim_matrix[i,j]= 1-(dist_matrix[row_indices[i]-1,col_indices[j]-1])
                    else:
                        sim_matrix[i,j]= (dist_matrix[row_indices[i]-1,col_indices[j]-1])
                        
    out_mat = out_prefix + '.mat'
    savemat(out_mat, { 'obj0': sim_matrix})
    
    out_nii = out_prefix + '.nii'
    niiheader = nb.nifti1.Nifti1Header()
    niiaffine = np.identity(4)
    niiaffine[3,3]=0
    nifti_image = nb.Nifti1Image(sim_matrix, niiaffine, niiheader)
    nb.save(nifti_image, out_nii)
    
    return op.abspath(out_mat), op.abspath(out_nii)



def merge_matrices(sm_left_left, sm_left_right, sm_right_left, sm_right_right, out_filename, save_as_nii=False ):


    import numpy as np
    import os.path as op
    import nibabel as nb
    from scipy.io import savemat
  
    full_matrix = np.concatenate((np.concatenate((nb.load(sm_left_left).get_data(), nb.load(sm_left_right).get_data()), axis=1),
                                  np.concatenate((nb.load(sm_right_left).get_data(),nb.load(sm_right_right).get_data() ), axis=1)), axis=0)

    if (save_as_nii):
        nImg = nb.Nifti1Image(full_matrix,None)
        nb.save(nImg,out_filename) 
    else:
        savemat(out_filename, { 'obj0': full_matrix})
    return op.abspath(out_filename)


def transpose_matrix(in_matrix, out_filename ):

    import numpy as np
    import os.path as op
    import nibabel as nb
    
    img = nb.load(in_matrix)
    transposed=np.transpose(img.get_data())
    nb.save(nb.Nifti1Image(transposed, img.get_affine(), img.get_header()), out_filename)
        
    return op.abspath(out_filename)

def mask_fs_matrix(in_matrix_nii, mask_row_nii, mask_col_nii, out_matrix_nii ):

    import numpy as np
    import os.path as op
    import nibabel as nb
    
    in_matrix = nb.load(in_matrix_nii).get_data()
    
    mask_row = nb.load(mask_row_nii).get_data()
    mask_row = mask_row.reshape(np.size(mask_row))
    row_indices = np.where(mask_row!=0)[0]
    
    mask_col = nb.load(mask_col_nii).get_data()
    mask_col = mask_col.reshape(np.size(mask_col))
    col_indices = np.where(mask_col!=0)[0]
    
    in_matrix = in_matrix[row_indices]
    in_matrix = in_matrix[:,col_indices]
    
    nImg = nb.Nifti1Image(in_matrix,None)
    nb.save(nImg,out_matrix_nii) 
        
    return op.abspath(out_matrix_nii)


def filled_image(tract_list, voxel_list_left, voxel_list_right):
    
    import nibabel as nb
    import numpy as np
    import os.path as op

    filled_name = 'filled_tract.nii'
    
    seed_tract = tract_list[0]
    tract_nii = nb.load(seed_tract)
    data = tract_nii.get_data()
    
    filled_data= np.ones_like(data, dtype=np.bool_)
    
    nb.save(nb.Nifti1Image(filled_data, tract_nii.get_affine(), tract_nii.get_header()),filled_name)
    
    arg_list_left = []
    arg_list_right = []
    
    for x, y, z in voxel_list_left:
        this_arg = "-bin -roi "+ str(x)+" 1 "+ str(y)+" 1 "+ str(z)+" 1 0 1 -kernel sphere 15 -dilM -binv"
        arg_list_left.append(this_arg)
        
    for x, y, z in voxel_list_right:
        this_arg = "-bin -roi "+ str(x)+" 1 "+ str(y)+" 1 "+ str(z)+" 1 0 1 -kernel sphere 15 -dilM -binv"
        arg_list_right.append(this_arg)
        
    return op.abspath(filled_name), arg_list_left, arg_list_right




"""
read a list of visitation maps, with masked roi seed and without,  and create a direct connectivity matrix
"""
def get_connectivity_matrix_masked(tract_list_left, tract_list_right, tract_list_masked_left, tract_list_masked_right, voxel_list_left, voxel_list_right, max_value):
    
    def get_connectivity_submatrix(tract_list_or, tract_list_masked, this_voxel_list,opposite_voxel_list,max_value):
        
        def get_seed_connectivities(in_seed_tract_or, in_seed_tract_masked,seedvoxel_list, seed_id):
            import nibabel
            import numpy as np
                        
            tract_masked_nii = nibabel.load(in_seed_tract_masked)
            tract_or_nii = nibabel.load(in_seed_tract_or)

            
            data_masked = tract_masked_nii.get_data()
            data_or = tract_or_nii.get_data()
            out_seed_connectivities=np.zeros(len(seedvoxel_list))
            index=0
            

            
            for x, y, z in seedvoxel_list:
                out_seed_connectivities[index]=data_masked[x,y,z]
                index += 1
                
            if(seed_id > 0):
                this_maxval = data_or[seedvoxel_list[seed_id][0],seedvoxel_list[seed_id][1],seedvoxel_list[seed_id][2]]
            else:
                this_maxval = 0
            
                                 
            return out_seed_connectivities, this_maxval
        
        import numpy as np
        from scipy.sparse import csr_matrix
        
        seed_dim_this=len(this_voxel_list)
        seed_dim_opposite=len(opposite_voxel_list)
        tract_dim=len(tract_list_masked)
        
        assert seed_dim_this == tract_dim, "voxel list and tract list dimensions dont match"
        
        zeroline_this = np.zeros((1,seed_dim_this))
        zeroline_opposite = np.zeros((1,seed_dim_opposite))
        
        exclusion_list = []
        exclusion_indexes = []
                
        submatrix_this=np.zeros((tract_dim,seed_dim_this))
        for i in xrange(tract_dim):
            [submatrix_this[i],this_maxval]=get_seed_connectivities(tract_list_or[i],tract_list_masked[i],this_voxel_list,i)
            if( this_maxval < max_value ):
                submatrix_this[i] = zeroline_this
                exclusion_indexes.append(i)
                exclusion_list.append(this_voxel_list[i])
        # check if diagonal elements are lower than 5000, if so, set to 0
            

        sparse_this = csr_matrix(submatrix_this)
        del(submatrix_this)
                           
        submatrix_opposite=np.zeros((tract_dim,seed_dim_opposite))
        for i in xrange(tract_dim):
            [submatrix_opposite[i],no_use]=get_seed_connectivities(tract_list_or[i],tract_list_masked[i],opposite_voxel_list, -1)
            
        for i in exclusion_indexes:
            submatrix_opposite[i] = zeroline_opposite
            
        sparse_opposite = csr_matrix(submatrix_opposite)
        del(submatrix_opposite)
                        
        return sparse_this, sparse_opposite, exclusion_list
            
    submatrix_left_left, submatrix_left_right, exclusion_left= get_connectivity_submatrix(tract_list_left, tract_list_masked_left, voxel_list_left, voxel_list_right, max_value)
    
    submatrix_right_right, submatrix_right_left, exclusion_right = get_connectivity_submatrix(tract_list_right, tract_list_masked_right, voxel_list_right, voxel_list_left, max_value)
    
    exclusion_list = []
    exclusion_list.extend(exclusion_left)
    exclusion_list.extend(exclusion_right)

    return submatrix_left_left, submatrix_left_right, submatrix_right_left, submatrix_right_right, exclusion_list


"""
# how to debug
if __name__ == '__main__':
    get_connectivity_matrix( INPUTS HERE )
"""
