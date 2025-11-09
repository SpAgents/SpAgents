import numpy as np
import SimpleITK as sitk
import pandas as pd
import monai
import torch
import torch.nn as nn
import torchvision.models as models
from scipy.ndimage import binary_dilation

import dashscope
from dashscope import Generation

import openai
import os


def load_model(model, config):
    """
    Loads the model weights from a specified path in the configuration.

    Parameters:
    - model (torch.nn.Module): The PyTorch model instance to load weights into.
    - config (dict): Configuration dictionary with the following keys:
        - "load_path" (str): Path to the saved model weights.
        - "is_dp" (bool): Whether the model was trained using DataParallel (DP).

    Returns:
    - torch.nn.Module: Model with loaded weights.
    """
    load_path = config["load_path"]
    is_dp = config["is_dp"]
    if is_dp:
        new_state_dict = {}
        for k, v in torch.load(load_path,map_location=torch.device('cpu')).items():
            new_state_dict[k[7:]] = v
        model.load_state_dict(new_state_dict)
    else:
        model.load_state_dict(torch.load(load_path,map_location=torch.device('cpu')))
    return model


def resnet18(in_channel, num_class):
    """
    Initializes a ResNet-18 model with custom input channels and output classes.

    Parameters:
    - in_channel (int): Number of input channels (e.g., 1 for grayscale, 3 for RGB).
    - num_class (int): Number of output classes.

    Returns:
    - torch.nn.Module: Customized ResNet-18 model.
    """
    resnet18_model = models.resnet18(pretrained=False)
    resnet18_model.conv1 = nn.Conv2d(in_channel, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False)
    resnet18_model.fc = nn.Linear(512, num_class)
    return resnet18_model

def resize_array_center(arr, target_shape):
    """
    Resizes a 2D array by cropping or padding it to the target shape, centered.

    Parameters:
    - arr (np.ndarray): Input 2D array.
    - target_shape (tuple): Desired shape (rows, cols).

    Returns:
    - np.ndarray: Resized array.
    """
    rows, cols = target_shape
    current_rows, current_cols = arr.shape

    # Calculate cropping indices
    start_row = max(0, (current_rows - rows) // 2)
    start_col = max(0, (current_cols - cols) // 2)

    end_row = start_row + rows
    end_col = start_col + cols

    # Crop the array
    resized_arr = arr[start_row:end_row, start_col:end_col]

    # Calculate padding sizes
    pad_row = max(0, (rows - resized_arr.shape[0]) // 2)
    pad_col = max(0, (cols - resized_arr.shape[1]) // 2)

    # Pad the array to match the target shape
    resized_arr = np.pad(resized_arr, ((pad_row, rows - resized_arr.shape[0] - pad_row), 
                                       (pad_col, cols - resized_arr.shape[1] - pad_col)), 
                        mode='constant', constant_values=0)

    return resized_arr

def ImageResample(sitk_img, new_size=[512, 512, 24], is_label=False):
    """
    Resamples an image using SimpleITK to a new size and spacing.

    Parameters:
    - sitk_img (SimpleITK.Image): Input image to be resampled.
    - new_size (list): Target size [width, height, depth].
    - is_label (bool): Whether the image is a label (uses nearest neighbor interpolation if True).

    Returns:
    - SimpleITK.Image: Resampled image.
    """
    size = np.array(sitk_img.GetSize())
    spacing = np.array(sitk_img.GetSpacing())
    
    # Calculate new spacing based on target size
    new_spacing_refine = size * spacing / new_size
    new_spacing_refine = [float(s) for s in new_spacing_refine]
    new_size = [int(s) for s in new_size]
    
    resample = sitk.ResampleImageFilter()
    resample.SetOutputDirection(sitk_img.GetDirection())
    resample.SetOutputOrigin(sitk_img.GetOrigin())
    resample.SetSize(new_size)
    resample.SetOutputSpacing(new_spacing_refine)
    
    # Set interpolation method
    if is_label:
        resample.SetInterpolator(sitk.sitkNearestNeighbor)
    else:
        resample.SetInterpolator(sitk.sitkBSpline)

    newimage = resample.Execute(sitk_img)
    return newimage

def resizeImageWithCropOrPad(image, img_size=(24, 512, 512), **kwargs):
    """
    Resizes a 3D image by cropping or padding to the specified size.

    Parameters:
    - image (np.ndarray): Input 3D array.
    - img_size (tuple): Desired image size (depth, height, width).
    - **kwargs: Additional arguments for np.pad.

    Returns:
    - np.ndarray: Resized image.
    """
    assert isinstance(image, (np.ndarray, np.generic))
    assert (image.ndim - 1 == len(img_size) or image.ndim == len(img_size)), \
        'Example size doesnt fit image size'

    rank = len(img_size)
    
    from_indices = [[0, image.shape[dim]] for dim in range(rank)]
    to_padding = [[0, 0] for dim in range(rank)]

    slicer = [slice(None)] * rank
    for i in range(rank):
        if image.shape[i] < img_size[i]:
            # Calculate padding
            to_padding[i][0] = (img_size[i] - image.shape[i]) // 2
            to_padding[i][1] = img_size[i] - image.shape[i] - to_padding[i][0]
        else:
            # Calculate cropping indices
            from_indices[i][0] = int(np.floor((image.shape[i] - img_size[i]) / 2.))
            from_indices[i][1] = from_indices[i][0] + img_size[i]

        slicer[i] = slice(from_indices[i][0], from_indices[i][1])

    return np.pad(image[slicer[0], slicer[1], slicer[2]], to_padding, **kwargs)

def linear_scale_image(image, up_quantile=99, low_quantile=1):
    """
    Linearly scales the pixel values of an image between 0 and 1 based on percentile thresholds.

    Parameters:
    - image (np.ndarray): Input image array.
    - up_quantile (float): Upper percentile for scaling.
    - low_quantile (float): Lower percentile for scaling.

    Returns:
    - np.ndarray: Scaled image array.
    """
    max_testue = np.percentile(image, up_quantile)
    min_testue = np.percentile(image, low_quantile)

    image = (image - min_testue) / (max_testue - min_testue)
    image = np.clip(image, 0, 1)
    return image

def find_consecutive_non_zero_layers(counts):
    """
    Finds the longest sequence of consecutive non-zero elements in a list.

    Parameters:
    - counts (list): List of counts or values.

    Returns:
    - list: Indices of the longest consecutive non-zero sequence.
    """
    consecutive_layers = []
    current_sequence = []
    for i, count in enumerate(counts):
        if count != 0:
            current_sequence.append(i)
        else:
            if current_sequence:
                consecutive_layers.append(current_sequence)
                current_sequence = []
    
    if current_sequence:
        consecutive_layers.append(current_sequence)
    longest_consecutive_sequence = max(consecutive_layers, key=len)
    return longest_consecutive_sequence   

class DataStore(object):
    """
    A class to store and manage patient data, image data, segmentation results, and analysis results.
    
    Attributes:
    - Patient Information:
        - patient_name (str): Name of the patient.
        - patient_id (str): Identifier of the patient.
        - patient_age (int): Age of the patient.
        - patient_sex (str): Sex of the patient.
        - patient_phase (str): Phase of the imaging process.
    
    - Image Data:
        - original_z (int): Original Z-axis dimension (depth).
        - original_image (SimpleITK.Image): Original medical image in SimpleITK format.
        - npy_image (np.ndarray): Numpy array of the original image.
        - seg1_image (np.ndarray): Numpy array for the first segmentation.
        - seg2_image (np.ndarray): Numpy array for the second segmentation.
    
    - Layer Information:
        - layer_list (list): List of all image layers.
        - start_layer (int): Starting layer index for a specific analysis (e.g., layer 0).
        - end_layer (int): Ending layer index for a specific analysis (e.g., layer 24).

    - Quadrant Analysis:
        - quadrant_id_list (list): List of quadrant IDs.
        - quadrant_image_list (list): List of numpy images for each quadrant.
        - quadrant_res_dict (dict): Dictionary storing scores for each quadrant.

    - Region-Level Analysis:
        - rl_id_list (list): List of region-level (RL) IDs.
        - rl_image_list (list): List of numpy images for region-level analysis.
        - rl_depth_res_dict (dict): Dictionary storing edema depth scores for RL analysis.
        - rl_intensity_res_dict (dict): Dictionary storing edema intensity scores for RL analysis.

    - Analysis Results:
        - sparcc_df (pd.DataFrame): DataFrame containing SPARCC (Sacroiliac Joint Scoring) results.
        - active_sacroiliitis_res (dict): Dictionary storing active sacroiliitis results.
        - report (str): Generated report based on analysis results.

    - Dictionaries:
        - quadrand_dict (dict): Mapping of quadrant IDs to anatomical names in Chinese.
        - rl_dict (dict): Mapping of RL IDs to analysis types in Chinese.
        - label_dict (dict): Mapping of quadrant IDs to numerical labels.
        - label_reserve_dict (dict): Reverse mapping of numerical labels to quadrant IDs.

    - Phase Information:
        - phase_priority (list): List of prioritized imaging phases.
        - phase (list): List of imaging phases available for analysis.
    """
    def __init__(self, config):
        """
        Initializes a DataStore instance with default values and configuration.

        Parameters:
        - config (dict): Configuration dictionary for initialization.
        """
        self.patient_name = None
        self.patient_id = None
        self.patient_age = None
        self.patient_sex = None
        self.patient_phase = None
        
        self.original_z = None
        
        self.original_image = None # sitk image
        self.npy_image = None # npy image
        self.seg1_image = None # npy image
        self.seg2_image = None # npy image
        self.layer_list = None # all layer
        self.start_layer = None # start layer of 24
        self.end_layer = None # end layer of 24
        
        self.quadrant_id_list = None # quadrant id
        self.quadrant_image_list = None # npy image list
        self.quadrant_res_dict = None # score list
        
        self.rl_id_list = None # rl id
        self.rl_image_list = None # npy image list
        self.rl_depth_res_dict = None # edema depth score list
        self.rl_intensity_res_dict = None # edema intensity score list
        
        self.sparcc_df = None # result dataframe
        self.active_sacroiliitis_res = None # active sacroiliitis result
        self.report = None # report generation
        
        self.quadrand_dict = {
            "iru": "髂骨右上",
            "sru": "骶骨右上",
            "ird": "髂骨右下",
            "srd": "骶骨右下",
            "slu": "骶骨左上",
            "ilu": "髂骨左上",
            "sld": "骶骨左下",
            "ild": "髂骨左下"
        }
        
        self.rl_dict = {
            "rdeep": "右侧深度",
            "rinten": "右侧亮度",
            "ldeep": "左侧深度",
            "linten": "左侧亮度"
        }
        
        self.label_dict  = {"iru":1, "sru":2, "ird":3, "srd":4, "slu":5, "ilu":6, "sld":7, "ild":8}
        self.label_reserve_dict = {1:"iru", 2:"sru", 3:"ird", 4:"srd", 5:"slu", 6:"ilu", 7:"sld", 8:"ild"}
        
        self.phase_priority = ['stir_fse_cor', 'T2_STIR_COR ', 'T2W_SPAIR ']
        self.phase = ['C12-T2 FSE COR FS, 16 slices', 'C4-T2 FSE COR FS, 16 slices ', 'COR STIR', 'OCor STIR ', 'pd_fse_cor_fs ', 'Obl. FSE STIR ', 'C10-T2 FSE COR FS, 16 slices', 'C4-T2 REVOLVE COR FS, 16 slices ', 't2_tse_fs_cor_200mm ']
    
    def change_varible(self, varible_name, varible_value):
        """
        Changes the value of an existing attribute.

        Parameters:
        - varible_name (str): Name of the attribute to change.
        - varible_value: New value for the attribute.

        Raises:
        - ValueError: If the attribute does not exist.
        """
        if not hasattr(self, varible_name):
            raise ValueError("No such varible.")
        setattr(self, varible_name, varible_value)
        return
    
    def clear_cache(self):
        """
        Clears all stored patient data, image data, and analysis results, resetting them to None.
        """
        self.patient_name = None
        self.patient_id = None
        self.patient_age = None
        self.patient_sex = None
        
        self.original_z = None
        
        self.original_image = None # sitk image
        self.npy_image = None # npy image
        self.seg1_image = None # npy image
        self.seg2_image = None # npy image
        self.layer_list = None # all layer
        self.start_layer = None # start layer of 24
        self.end_layer = None # end layer of 24
        
        self.quadrant_id_list = None # quadrant id
        self.quadrant_image_list = None # npy image list
        self.quadrant_res_dict = None # score list
        
        self.rl_id_list = None # rl id
        self.rl_image_list = None # npy image list
        self.rl_depth_res_dict = None # edema depth score list
        self.rl_intensity_res_dict = None # edema intensity score list
        
        self.sparcc_df = None # result dataframe
        self.active_sacroiliitis_res = None # active sacroiliitis result
        self.report = None # report generation
        return


class EdemaSystem(object):
    """
    EdemaSystem Class

    Overview:
    -----------
    The `EdemaSystem` class is designed to provide a comprehensive pipeline for edema detection, recognition, 
    and report generation based on medical imaging data, specifically targeting conditions like active sacroiliitis.
    The system leverages deep learning models to perform classification tasks and generate insights based on 
    the detected features, supporting the diagnosis of conditions such as ankylosing spondylitis (AS).

    Key Functionalities:
    ----------------------
    1. Data Preprocessing and Initialization:
    - Initializes necessary attributes and data structures using the provided `DataStore` object.
    - Loads pre-trained deep learning models for various classification tasks (e.g., quadrant classification, depth, and intensity classification).

    2. Edema Recognition:
    - `run_edema_recognition_module()`: Main function for edema recognition, utilizing multiple models to classify images.
    - `classify_inference()`: Classifies quadrant images based on input data using a pre-trained classification model.
    - `classify_depth_intensity_inference()`: Classifies images for depth and intensity analysis using separate models.

    3. Feature Extraction and SPARCC Score Calculation:
    - `get_sparcc_df()`: Constructs a DataFrame containing SPARCC (Sacroiliac Joint Inflammation) scores for each identified region, based on model predictions.
    - `merge_dicts_with_same_keys()`: Utility function to merge dictionaries with common keys, helping aggregate results for specific image segments.

    4. Active Sacroiliitis Detection:
    - `get_active_sacroiliitis_by_data_driven()`: Detects the presence of active sacroiliitis based on predefined criteria, such as edema spread across multiple quadrants or consecutive layers.

    5. Report Generation:
    - `run_report_generation_model()`: Compiles a comprehensive diagnostic report, including patient information, SPARCC scores, edema distribution, and active sacroiliitis assessment.
    - `get_patient_info_text()`, `get_sparcc_text()`, `get_layers_edema_text()`, `get_single_layer_edema_text()`: Helper functions for constructing specific sections of the diagnostic report.
    - `get_active_sacroiliitis_reason()`: Provides a detailed explanation of the reasons behind the diagnosis, including the identification of consecutive layers with edema.

    6. Recommendations and Suggestions:
    - `get_recommendation_prompt()`: Prepares a text prompt based on edema information for generating diagnostic recommendations.
    - `get_recommendation_text()`: Uses a language model (e.g., OpenAI API) to generate recommendations based on the edema findings.

    7. Cache and Resource Management:
    - `clear_data_cache()`: Clears cached data within the `DataStore` object to free up memory and ensure clean state for new analysis.
    - `clear_model_cache()`: Resets the internal state of models and tokenizers, releasing memory and avoiding potential conflicts during subsequent inferences.

    Design Considerations:
    ------------------------
    - The system is modular and extensible, allowing for the addition of new classification models or diagnostic rules.
    - The pipeline handles various edge cases, such as missing data or failed predictions, with error handling and logging.
    - The system integrates deep learning inference with data-driven diagnostic rules, combining model predictions with traditional medical criteria for more robust assessments.

    Usage:
    -------
    The `EdemaSystem` class is intended for use in automated diagnostic pipelines or clinical decision support systems (CDSS). 
    It requires a pre-configured `DataStore` object with loaded image data and metadata. The class methods can be called 
    sequentially or integrated into a larger workflow for processing and reporting medical imaging data.

    Example:
    ---------
    ```python
    import sys
    sys.path.append(".")
    from EdemaSystem import EdemaSystem
    from scipy.ndimage import binary_dilation

    config = {
        "threshold": 2500,
        "api_key": "XXXX",
        "seg_type": "two_stage",
        "seg_1_model":{
            "load_path": "XXXX.pth",
            "is_dp": False
            },
        "seg_2_model":{
            "load_path": "XXXX.pth",
            "is_dp": False
            },
        "classify_model":{
            "load_path": "XXXX.pth",
            "is_dp": False
            },
        "classify_depth_model":{
            "load_path": "XXXX.pth",
            "is_dp": False
            },
        "classify_intensity_model":{
            "load_path": "XXXX.pth",
            "is_dp": False
            },
    }


    test_system = EdemaSystem(config)
    report = test_system.run("../DATA/ID")
    print(report)
    """

    def __init__(self, config):
        """
        Initialize the EdemaSystem class.

        Args:
            config (dict): Configuration dictionary containing model paths and parameters.

        Attributes:
            device (torch.device): Computation device ('cuda' if available, otherwise 'cpu').
            data_store (DataStore): Instance of DataStore to manage patient data.
            threshold (float): Threshold value for classification.
            seg_1_model (nn.Module): First-stage segmentation model.
            seg_2_model (nn.Module): Second-stage segmentation model.
            classify_model (nn.Module): Model for edema classification.
            classify_depth_model (nn.Module): Model for classifying edema depth.
            classify_intensity_model (nn.Module): Model for classifying edema intensity.
            language_model (object): Language model for report generation (OpenAI).
            softmax_layer (nn.Softmax): Softmax activation function for classification outputs.
        """
        self.config = config
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.data_store = DataStore(self.config)

        self.threshold = config["threshold"]

        self.seg_1_model = None
        self.seg_2_model = None
        self.classify_model = None
        self.classify_depth_model = None
        self.classify_intensity_model = None
        self.language_model = None
        self.softmax_layer = nn.Softmax(dim=1)
        # self.sigmoid_layer = nn.Sigmoid()
        
        self.load_seg_model()
        self.load_classify_model()
        self.load_language_model()
        
    
        
    def load_image_test(self):
        """
        Load a test image from a specified folder path.

        Reads the image using SimpleITK and stores it in the `original_image` attribute.
        """
        image_folder_path = self.config["image_folder_path"]
        self.original_image = sitk.ReadImage(image_folder_path)
        return
    
    def run_sparcc_score(self, npy_img_path, patient_id):
        print(f"[DEBUG] Loading preprocessed NPY: {npy_img_path}")
        npy_img = np.load(npy_img_path)
        print(f"[DEBUG] Shape: {npy_img.shape}")

        self.data_store.change_varible("npy_image", npy_img)
        self.data_store.change_varible("original_z", npy_img.shape[0])
        self.data_store.change_varible("patient_id", patient_id)

        try:
            self.run_segmentation_module()
            print("[DEBUG] Segmentation done.")
        except Exception as e:
            print(f"[ERROR] Segmentation error: {e}")
            raise

        try:
            self.run_edema_recognition_module()
            print("[DEBUG] Edema recognition done.")
        except Exception as e:
            print(f"[ERROR] Edema recognition error: {e}")
            raise

        sparcc_df = self.data_store.sparcc_df
        self.clear_data_cache()
        return sparcc_df
        
        
        
    
    def run(self, dicom_path):
        """
        Main function to process a DICOM image and generate a report.

        Args:
            dicom_path (str): Path to the DICOM directory.

        Returns:
            str: Generated report stored in `DataStore`.
        """
        self.load_image_by_dicom_path(dicom_path)
        #self.run_preprocess_module()
        self.run_segmentation_module()
        self.run_edema_recognition_module()
        self.run_report_generation_model()
        report = self.data_store.report
        self.clear_data_cache()
        return report
    
    def load_image_by_dicom_path(self, dicom_path):
        """
        Load a DICOM image from the specified path and extract patient metadata.

        Args:
            dicom_path (str): Path to the DICOM directory.

        Raises:
            ValueError: If no valid phase is found in the DICOM series.
        """
        series_id_list = sitk.ImageSeriesReader.GetGDCMSeriesIDs(dicom_path)
        series_id = ""
        series_id_backup = ""
        phase_backup = ""
        
        # Iterate through all series IDs to find the preferred phase
        for item in series_id_list:
            series_file_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(dicom_path, item)
            file_reader = sitk.ImageFileReader()
            file_reader.SetFileName(series_file_names[0])
            file_reader.ReadImageInformation()
            try:
                phase = file_reader.GetMetaData("0008|103e")
            except:
                continue
            
            # Check if the phase is in the priority list
            if phase in self.data_store.phase_priority:
                series_id = item
                break
            if phase in self.data_store.phase:
                series_id_backup = item
                phase_backup = phase
        
        # Use backup phase if no priority phase is found
        if series_id == "":
            series_id = series_id_backup
            phase = phase_backup
        if series_id == "":
            raise ValueError("No phase found.")
        
        # Update `DataStore` with phase information
        self.data_store.change_varible("patient_phase", phase)
        series_file_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(dicom_path, series_id)
        series_reader = sitk.ImageSeriesReader()
        series_reader.SetFileNames(series_file_names)
        images = series_reader.Execute()
        
        # Store the original image in `DataStore`
        self.data_store.change_varible("original_image", images)
        
        file_reader = sitk.ImageFileReader()
        file_reader.SetFileName(series_file_names[0])
        file_reader.ReadImageInformation()
        keys = file_reader.GetMetaDataKeys()
        if "0010|0010" in keys:
            self.data_store.change_varible("patient_name", file_reader.GetMetaData("0010|0010"))
        if "0010|0020" in keys:
            self.data_store.change_varible("patient_id", file_reader.GetMetaData("0010|0020"))
        if "0010|1010" in keys:
            self.data_store.change_varible("patient_age", file_reader.GetMetaData("0010|1010"))
        if "0010|0040" in keys:
            self.data_store.change_varible("patient_sex", file_reader.GetMetaData("0010|0040"))
        return
    
    def load_seg_model(self):
        """
        Load segmentation models (two-stage segmentation).

        Raises:
            ValueError: If the segmentation model type is not 'two_stage' or if model loading fails.
        """
        if not (self.config["seg_type"] == "two_stage"):
            raise ValueError("Type of seg model is not two stage seg.")
        
        # Load first-stage segmentation model
        try:
            self.seg_1_model = monai.networks.nets.BasicUNet(spatial_dims=3, in_channels=1, out_channels=2, features=(16,16,32,64,128,16)).to(self.device)
            seg_1_model_config = self.config["seg_1_model"]
            self.seg_1_model = load_model(self.seg_1_model, seg_1_model_config)
            self.seg_1_model.eval()
        except Exception as e:
            print(e)
            raise ValueError("Seg_1_model load fail.")
        
        # Load second-stage segmentation model
        try:
            self.seg_2_model = monai.networks.nets.BasicUNet(spatial_dims=3, in_channels=2, out_channels=9, features=(16,16,32,64,128,16)).to(self.device)
            seg_2_model_config = self.config["seg_2_model"]
            self.seg_2_model = load_model(self.seg_2_model, seg_2_model_config)
            self.seg_2_model.eval()
        except Exception as e:
            print(e)
            raise ValueError("Seg_2_model load fail.")
        return
    
    def load_classify_model(self):
        """
        Load classification models for edema recognition.

        Raises:
            ValueError: If any classification model fails to load.
        """
        # Load classification model
        try:
            self.classify_model = resnet18(1, 2).to(self.device)
            classify_model_config = self.config["classify_model"]
            self.classify_model = load_model(self.classify_model, classify_model_config)
            self.classify_model.eval()
        except Exception as e:
            print(e)
            raise ValueError("Classify_model load fail.")
        
        # Load depth classification model
        try:
            self.classify_depth_model = resnet18(1, 2).to(self.device)
            classify_depth_model_config = self.config["classify_depth_model"]
            self.classify_depth_model = load_model(self.classify_depth_model, classify_depth_model_config)
            self.classify_depth_model.eval()
        except Exception as e:
            print(e)
            raise ValueError("Classify_depth_model load fail.")
        
        # Load intensity classification model
        try:
            self.classify_intensity_model = resnet18(1, 2).to(self.device)
            classify_intensity_model_config = self.config["classify_intensity_model"]
            self.classify_intensity_model = load_model(self.classify_intensity_model, classify_intensity_model_config)
            self.classify_intensity_model.eval()
        except Exception as e:
            print(e)
            raise ValueError("Classify_intensity_model load fail.")
        
        return
    
    def load_language_model(self):
        """
        Load the language model for report generation.

        Sets the OpenAI API key and base URL for model interaction.
        """
        # openai.api_key = self.config["api_key"]
        openai.api_key = "none"
        openai.api_base = "http://172.17.101.235:8990/v1"#http://172.17.102.193:8990/v1
        return
    
    def run_preprocess_module(self):
        """
        Preprocess the input image by resampling, resizing, and applying linear scaling.

        This function resizes the image to a fixed size (512x512) if the original dimensions differ, 
        then resizes the image to a target size, applies linear scaling, and stores the resulting array 
        in the data store.
        """
        image = self.data_store.original_image
        x,y,z = self.data_store.original_image.GetSize()
        self.data_store.change_varible("original_z", z)
        
        # Resize image to 512x512 if dimensions are not equal to 512
        if (x != 512) | (y != 512):
            image = ImageResample(image, new_size=[512, 512, z])
            
        # Convert image to numpy array and preprocess it
        image_arr = sitk.GetArrayFromImage(image)
         # Resize to target size
        image_arr = resizeImageWithCropOrPad(image_arr, img_size=(24, 512, 512))
        # Apply linear scaling
        image_arr = linear_scale_image(image_arr)
        # Ensure correct data type for further processing
        image_arr = image_arr.astype(np.float32)
        
        # Store the preprocessed image in the data store
        self.data_store.change_varible("npy_image", image_arr)
        return
    
    def run_segmentation_module(self):
        """
        Run the two-stage segmentation model to segment the image into regions of interest.

        This function performs first and second stage segmentation and stores the results in the data store.
        """
        npy_image = self.data_store.npy_image
        seg_1_image = self.seg_1_inference(npy_image)
        seg_2_image = self.seg_2_inference(npy_image, seg_1_image)
        # Store segmentation results
        self.data_store.change_varible("seg1_image", seg_1_image)
        self.data_store.change_varible("seg2_image", seg_2_image)
        # Get the regions of interest from the segmentation
        self.get_roi_image()
        return
    
    def seg_1_inference(self, npy_image):
        """
        Perform inference using the first-stage segmentation model.

        Args:
            npy_image (numpy.ndarray): The preprocessed image to be segmented.

        Returns:
            numpy.ndarray: The first-stage segmentation result.
        """
        try:
            img = torch.from_numpy(npy_image).float()
            # Add batch and channel dimensions
            img = img.unsqueeze(0).unsqueeze(0)
            img = img.to(self.device)
            
            # Get segmentation prediction from the model
            pred = self.seg_1_model(img)
            # Apply softmax to the output
            pred = self.softmax_layer(pred)
            # Get the predicted class for each pixel
            pred = torch.argmax(pred, dim=1)
            # Remove unnecessary dimensions
            pred = pred.squeeze()
            # Convert tensor to numpy array
            pred = np.asarray(pred.cpu())
            return pred
        except Exception as e:
            print(e)
            raise ValueError("Seg_1_inference fail.")
    
    def seg_2_inference(self, npy_image, seg_1_image):
        """
        Perform inference using the second-stage segmentation model, which takes both the original image 
        and the first-stage segmentation results as input.

        Args:
            npy_image (numpy.ndarray): The preprocessed image.
            seg_1_image (numpy.ndarray): The result of the first-stage segmentation.

        Returns:
            numpy.ndarray: The second-stage segmentation result.
        """
        try:
            img = torch.from_numpy(npy_image).float()
            seg1 = torch.from_numpy(seg_1_image).float()
            
            # Concatenate the image and first-stage segmentation result along the channel dimension
            img = img.unsqueeze(0)
            seg1 = seg1.unsqueeze(0)
            img = torch.cat((img, seg1), dim=0)
            img = img.unsqueeze(0)
            img = img.to(self.device)
            
            # Get segmentation prediction from the second-stage model
            pred = self.seg_2_model(img)
            pred = self.softmax_layer(pred)
            pred = torch.argmax(pred, dim=1)
            pred = pred.squeeze()
            pred = np.asarray(pred.cpu())
            return pred
        except Exception as e:
            print(e)
            raise ValueError("Seg_2_inference fail.")
        return
    
    def get_roi_image(self):
        """
        Extract regions of interest (ROIs) from the segmented image based on the segmentation mask.

        This function identifies and extracts regions corresponding to specific labels and stores them in the data store.
        """
        # Get segmentation results and other relevant data
        image_arr = self.data_store.npy_image
        mask_arr = self.data_store.seg2_image
        threshold = self.threshold
        patient_id = self.data_store.patient_id
        original_z = self.data_store.original_z
        label_dict = self.data_store.label_dict
        
        layer_count = np.count_nonzero(mask_arr, axis=(1, 2))
        layer_list = find_consecutive_non_zero_layers(layer_count)
        remove_layer = []
        
        quadrant_id_list = []
        quadrant_image_list = []
        rl_id_list = []
        rl_image_list = []
        
        # Process each layer to extract regions of interest
        for layer_i in layer_list:
            slice_i = mask_arr[layer_i]
            slice_mask = np.where(slice_i > 0, 1, 0) 
            slice_mask_type = np.unique(slice_i)
            
            # Skip layers that don't meet the threshold
            if np.sum(slice_mask) < threshold:
                remove_layer.append(layer_i)
                continue
            layer_id = layer_i - (24-original_z) / 2 + 1
            img_i = image_arr[layer_i]
            
            for key, value in label_dict.items():
                if value not in slice_mask_type:
                    continue
                else:
                    # Process the slice for the identified region
                    layer_str_id = patient_id + "_" + str(int(layer_id)) + "_" + key
                    slice_mask_i = np.where(slice_i == value, 1, 0)
                    slice_mask_i = binary_dilation(slice_mask_i, iterations=1)
                    slice_mask_i = binary_dilation(slice_mask_i, iterations=1)
                    x, y = np.where(slice_mask_i == 1)
                    if len(x) == 0:
                        continue
                    
                    # Extract the region of interest and store it
                    img_j = img_i.copy()
                    img_j[~slice_mask_i] = 0
                    img_j = img_j[x.min():x.max(), y.min():y.max()]
                    quadrant_id_list.append(layer_str_id)
                    quadrant_image_list.append(img_j)
            
            # Remove specific regions (right/left) from the mask and extract the regions
            slice_mask_r = slice_i.copy()
            slice_mask_r[(slice_mask_r==5)|(slice_mask_r==6)|(slice_mask_r==7)|(slice_mask_r==8)] = 0
            slice_mask_r = np.where(slice_mask_r > 0, 1, 0)
            x, y = np.where(slice_mask_r == 1)
            if not (len(x) == 0):
                img_r = img_i[np.min(x):np.max(x), np.min(y):np.max(y)]
                rl_id_list.append(patient_id + "_" + str(int(layer_id)) + "_r")
                rl_image_list.append(img_r)
            
            slice_mask_l = slice_i.copy()
            slice_mask_l[(slice_mask_l==1)|(slice_mask_l==2)|(slice_mask_l==3)|(slice_mask_l==4)] = 0
            slice_mask_l = np.where(slice_mask_l > 0, 1, 0)
            x, y = np.where(slice_mask_l == 1)
            if not (len(x) == 0):
                img_l = img_i[np.min(x):np.max(x), np.min(y):np.max(y)]
                rl_id_list.append(patient_id + "_" + str(int(layer_id)) + "_l")
                rl_image_list.append(img_l)
        
        # Similarly process the left regions
        for layer_i in remove_layer:
            layer_list.remove(layer_i)
        self.data_store.change_varible("layer_list", layer_list)
        self.data_store.change_varible("quadrant_id_list", quadrant_id_list)
        self.data_store.change_varible("quadrant_image_list", quadrant_image_list)
        self.data_store.change_varible("rl_id_list", rl_id_list)
        self.data_store.change_varible("rl_image_list", rl_image_list)
        
        # Store the start and end layers based on the processed layers
        layer_start = layer_list[0] - (24-original_z) / 2 + 1
        layer_end = layer_list[-1] - (24-original_z) / 2 + 1
        self.data_store.change_varible("start_layer", layer_start)
        self.data_store.change_varible("end_layer", layer_end)
        return
    
    
    def run_edema_recognition_module(self):
        """
        This method coordinates the edema recognition process by classifying regions of interest (quadrants) 
        and regions of interest with depth and intensity (RL). The results are stored in the data store, 
        and the final processed report is generated by calling other helper functions.
        """
        # Classify quadrants based on image data
        quadrant_res_dict = self.classify_inference(self.data_store.quadrant_image_list, self.data_store.quadrant_id_list)
        
        # Classify regions of interest with depth and intensity
        rl_depth_res_dict, rl_intensity_res_dict = self.classify_depth_intensity_inference(self.data_store.rl_image_list, self.data_store.rl_id_list)
        
        # Store the results in the data store for later use
        self.data_store.change_varible("quadrant_res_dict", quadrant_res_dict)
        self.data_store.change_varible("rl_depth_res_dict", rl_depth_res_dict)
        self.data_store.change_varible("rl_intensity_res_dict", rl_intensity_res_dict)
        
        # Generate and store the sparcc dataframe based on classification results
        sparcc_df = self.get_sparcc_df(quadrant_res_dict, rl_depth_res_dict, rl_intensity_res_dict)
        self.data_store.change_varible("sparcc_df", sparcc_df)
        
        # Determine if active sacroiliitis is present based on the results
        active_sacroiliitis_res = self.get_active_sacroiliitis_by_data_driven()
        self.data_store.change_varible("active_sacroiliitis_res", active_sacroiliitis_res)
        return

    def classify_inference(self, image_list, image_id_list):
        """
        This method classifies the provided images using the specified classification model.
        It predicts the class for each image and stores the results in a dictionary.
        The method returns a dictionary with image IDs as keys and their corresponding classification results as values.
        """
        
        # Dictionary to store classification results, where keys are image IDs and values are classification predictions
        res_dict = dict()
        
        # Iterate over all images and classify each one
        for i in range(len(image_list)):
            try:
                # Retrieve the current image and its associated ID
                img = image_list[i]
                img_id = image_id_list[i]
                # Preprocess the data
                img = resize_array_center(img, (64, 64))
                img = torch.from_numpy(img).float()
                img = img.unsqueeze(0).unsqueeze(0)
                img = img.to(self.device)
                
                # Perform classification using the specified model
                pred = self.classify_model(img)
                
                # Postprocess the prediction
                pred = self.softmax_layer(pred)
                pred = torch.argmax(pred, dim=1)
                pred = pred.squeeze()
                pred = np.asarray(pred.cpu())
                
                # Convert the prediction to an integer and store it in the dictionary
                pred = int(pred)
                res_dict[img_id] = pred
                
            except Exception as e:
                print(e)
        # Return the dictionary containing the classification results
        return res_dict
    
    def classify_depth_intensity_inference(self, image_list, image_id_list):
        """
        This method classifies the images for depth and intensity using separate models. 
        It performs classification for each image in the provided list and returns two dictionaries:
        one for depth classification and one for intensity classification.
        """
        
        # Dictionaries to store classification results for depth and intensity, where keys are image IDs and values are classifications
        depth_res_dict = dict()
        intensity_res_dict = dict()
        
        # Iterate over all images and classify each one
        for i in range(len(image_list)):
            try:
                # Retrieve the current image and its associated ID
                img = image_list[i]
                img_id = image_id_list[i]
                
                # Preprocess the data
                img = resize_array_center(img, (128, 128))
                img = torch.from_numpy(img).float()
                img = img.unsqueeze(0).unsqueeze(0)
                img = img.to(self.device)
                
                # Perform classification for depth using the specified model
                pred = self.classify_depth_model(img)
                pred = self.softmax_layer(pred)
                pred = torch.argmax(pred, dim=1)
                pred = pred.squeeze()
                pred = np.asarray(pred.cpu())
                
                # Convert the prediction to an integer and store it in the dictionary
                pred = int(pred)
                depth_res_dict[img_id] = pred
                
                # Perform classification for intensity using the specified model
                pred1 = self.classify_intensity_model(img)
                pred1 = self.softmax_layer(pred1)
                pred1 = torch.argmax(pred1, dim=1)
                pred1 = pred1.squeeze()
                pred1 = np.asarray(pred1.cpu())
                
                # Convert the prediction to an integer and store it in the dictionary
                pred1 = int(pred1)
                
                # Store the intensity classification results in the dictionary
                intensity_res_dict[img_id] = pred1
            except Exception as e:
                print(e)
        
        # Return both depth and intensity classification result dictionaries
        return depth_res_dict, intensity_res_dict

    def get_sparcc_df(self, quadrant_res_dict, rl_depth_res_dict, rl_intensity_res_dict):
        """
        This method generates a DataFrame containing the results of the quadrant, depth, and intensity classifications.
        It combines the results from the three classification steps into a structured DataFrame.
        
        The DataFrame includes the following columns:
        - ID: the patient ID and layer information
        - iru, sru, ird, srd, etc.: classification results for different regions
        """
        
        # Extract the image IDs from the classification result dictionaries
        id1 = quadrant_res_dict.keys() # XXXXX_4_iru
        id2 = rl_depth_res_dict.keys() # XXXXX_4_rdeep/ldeep
        id3 = rl_intensity_res_dict.keys()
        
        # Generate unique layer IDs based on the image ID, using the first two parts of the string (patient ID and layer)
        layer_id1 = set([i.split("_")[0]+"_"+i.split("_")[1] for i in id1])
        layer_id2 = set([i.split("_")[0]+"_"+i.split("_")[1] for i in id2])
        layer_id3 = set([i.split("_")[0]+"_"+i.split("_")[1] for i in id3])
        
        # Combine all the layer IDs from the three dictionaries into a single list
        layer_id = list(layer_id1 | layer_id2 | layer_id3)
        
        # Define the columns for the DataFrame
        column = ["ID","iru","sru","ird","srd","rdeep","rinten","slu","ilu","sld","ild","ldeep","linten"]
        
        # Create an empty DataFrame with the specified columns
        sparcc_df = pd.DataFrame(data=None, columns=column)
        sparcc_df["ID"] = layer_id
        sparcc_df["layer_num"] = [int(i.split("_")[1]) for i in layer_id]
        
        # Sort the DataFrame by the layer number and reset the index
        sparcc_df.sort_values(by="layer_num", inplace=True)
        sparcc_df.reset_index(drop=True, inplace=True)
        
        # Populate the DataFrame with the quadrant classification results
        for key, value in quadrant_res_dict.items():
            q_layer_id = key.split("_")[0]+"_"+key.split("_")[1]
            col_name = key.split("_")[2]
            sparcc_df.loc[sparcc_df["ID"]==q_layer_id, col_name] = value
        
        # Populate the DataFrame with the depth classification results
        for key, value in rl_depth_res_dict.items():
            q_layer_id = key.split("_")[0]+"_"+key.split("_")[1]
            col_name = key.split("_")[2]
            sparcc_df.loc[sparcc_df["ID"]==q_layer_id, col_name] = value
            
        # Populate the DataFrame with the intensity classification results
        for key, value in rl_intensity_res_dict.items():
            q_layer_id = key.split("_")[0]+"_"+key.split("_")[1]
            col_name = key.split("_")[2]
            sparcc_df.loc[sparcc_df["ID"]==q_layer_id, col_name] = value
        sparcc_df.fillna(0, inplace=True)
        return sparcc_df

    def get_active_sacroiliitis_by_data_driven(self):
        """
        This method determines whether active sacroiliitis is present based on the SPARCC scores.
        It evaluates both the cumulative score across all regions and checks if consecutive regions are affected in a specific pattern.

        The method updates the `active_sacroiliitis_res` in the data store:
        - If the cumulative sum of SPARCC scores for any region reaches or exceeds 4, active sacroiliitis is flagged as present (1).
        - Additionally, if a region is affected in three consecutive layers, it also flags active sacroiliitis as present.
        
        Returns:
        - True if active sacroiliitis is detected.
        - False otherwise.
        """
        
        # Retrieve the SPARCC DataFrame from the data store
        df = self.data_store.sparcc_df

        # Define the regions to check for edema or abnormalities
        col_list = ["iru", "sru", "ird", "srd", "slu", "ilu", "sld", "ild"]
        
        # Initialize a variable to accumulate the SPARCC score
        sum1 = 0
        
        # Loop through the DataFrame to check the cumulative score for each layer
        for i in range(len(df)):
            sum1 += df.loc[i, col_list].sum()
            if sum1 >= 4:
                self.data_store.active_sacroiliitis_res = 1
                return True

        # Loop through the DataFrame to check for consecutive regions affected in 3 consecutive layers
        for i in range(len(df)-2):
            for col in col_list:
                if df.loc[i, col] == 1 and df.loc[i+1, col] == 1 and df.loc[i+2, col] == 1:
                    self.data_store.active_sacroiliitis_res = 1
                    return True
        # If no condition for active sacroiliitis was met, return False
        return False

    
    def run_report_generation_model(self):
        """
        This method generates a comprehensive report based on the analysis and findings of the image data.
        It gathers various sections of the report (e.g., patient info, SPARCC score, edema distribution, and recommendations)
        and combines them into a single string.

        The report is then stored in the data store and can be accessed for further use or export.
        """
        
         # Retrieve start and end layer information for the region of interest (ROI)
        roi_start_layer = self.data_store.start_layer
        roi_end_layer = self.data_store.end_layer
        
        # Get the SPARCC DataFrame and active sacroiliitis result from the data store
        sparcc_df = self.data_store.sparcc_df
        active_sacroiliitis_res = self.data_store.active_sacroiliitis_res
        
        # Collect various sections of the report using helper methods
        patient_info_text = self.get_patient_info_text()
        sparcc_score_text = self.get_sparcc_text(sparcc_df)
        layer_text = self.get_layers_edema_text(sparcc_df, roi_start_layer, roi_end_layer)
        active_sacroiliitis_reason_text = self.get_active_sacroiliitis_reason(sparcc_df, roi_start_layer, roi_end_layer)
        active_res_text = self.get_active_sacroiliitis_text(active_sacroiliitis_res)
        
        # Combine all sections into a full report
        all_text = patient_info_text + sparcc_score_text + layer_text + active_sacroiliitis_reason_text + active_res_text + "\n"
        
        # Generate recommendations based on the report content
        recommend = self.get_recommendation_text(all_text)
        # Store the full report (including recommendations) in the data store
        self.data_store.change_varible("report", all_text + recommend)
        
        # Return after the report generation is complete
        return
    
    def get_patient_info_text(self):
        """
        This helper method generates the patient information section of the report.
        It includes the patient's name, ID, age, and sex, if available.
        
        Returns:
        - A string containing the formatted patient information.
        """
        # Start the text with a header for patient information
        text = "患者信息：\n"
        
        # Append patient's details if they are available in the data store
        if self.data_store.patient_name is not None:
            text += "——姓名：{}\n".format(self.data_store.patient_name)
        if self.data_store.patient_id is not None:
            text += "——ID：{}\n".format(self.data_store.patient_id)
        if self.data_store.patient_age is not None:
            text += "——年龄：{}\n".format(self.data_store.patient_age)
        if self.data_store.patient_sex is not None:
            text += "——性别：{}\n".format(self.data_store.patient_sex)
        return text
    
    def get_sparcc_text(self, sparcc_df):
        """
        This helper method generates the SPARCC score summary section of the report.
        It sums up the SPARCC scores for each region and provides the total score.
        
        Returns:
        - A string containing the SPARCC score summary.
        """
        
        # Initialize the total SPARCC score
        sparcc = 0
        
        # Sum the SPARCC scores for all quadrants and regions of interest
        for key in self.data_store.quadrand_dict.keys():
            sparcc += sum(sparcc_df[key])
        for key in self.data_store.rl_dict.keys():
            sparcc += sum(sparcc_df[key])
            
        # Generate and return the SPARCC score text
        text = "SPARCC总分为{}分。\n".format(sparcc)
        return text
    
    def get_layers_edema_text(self, sparcc_df, roi_start_layer, roi_end_layer):
        """
        This helper method generates a text description of the edema distribution across the layers.
        It iterates through the layers of the image data and provides a summary of which regions show edema or abnormalities.
        
        Returns:
        - A string summarizing the edema distribution across layers.
        """
        
        # Start the section with a header for edema distribution
        layer_text = "患者水肿分布情况如下：\n"
        
        # Loop through the layers and describe edema for each layer in the specified ROI range
        for i in range(len(sparcc_df)):
            layer_text += "——第{}层：".format(roi_start_layer+i)
            sub_df = sparcc_df.loc[i]
            layer_text += self.get_single_layer_edema_text(sub_df)
        return layer_text
    
    def get_single_layer_edema_text(self, sub_df):
        """
        This helper method generates a description of edema for a single layer.
        It checks each region for edema and returns a string describing the regions affected.
        
        Returns:
        - A string describing the edema in the given layer.
        """
        text1 = ""
        
        # Check each region for edema and build a description for the quadrants
        for key in self.data_store.quadrand_dict.keys():
            if sub_df[key] == 1:
                text1 += self.data_store.quadrand_dict[key] + "，"
        if text1 != "":
            text1 += "出现水肿。"
        text2 = ""
        
        # Check each region for abnormalities and build a description for the regions of interest
        for key in self.data_store.rl_dict.keys():
            if sub_df[key] == 1:
                text2 += self.data_store.rl_dict[key] + "，"
        if text2 != "":
            text2 += "出现异常。"
        
        if text1 == "" and text2 == "":
            # If no edema or abnormalities are found, return a default message
            return "该层无水肿。\n"
        else:
            # Return the combined description of edema and abnormalities
            return text1 + text2 + "\n"
        
    def merge_dicts_with_same_keys(self, lst):
        """
        This helper method merges a list of dictionaries with the same keys.
        For each key, it accumulates and de-duplicates the values.
        
        Args:
        - lst (list): A list of dictionaries where each dictionary contains a key and a list of values.
        
        Returns:
        - merged_dict (dict): A dictionary where each key has a combined list of unique values.
        """
        merged_dict = {}
        
         # Iterate through each dictionary in the input list
        for d in lst:
            # Iterate through key-value pairs in the current dictionary
            for key, value in d.items():
                # If the key already exists in the merged dictionary, extend its value list
                if key in merged_dict:
                    merged_dict[key].extend(value)
                else:
                    # Otherwise, initialize the key with the current value list
                    merged_dict[key] = value
        
        # De-duplicate the values for each key by converting the list to a set and back to a list
        for key, value in merged_dict.items():
            merged_dict[key] = list(set(value))
        return merged_dict 

    def get_active_sacroiliitis_reason(self, df, roi_start_layer, roi_end_layer):
        """
        This method generates a textual explanation for the presence of active sacroiliitis based on the SPARCC DataFrame.
        It checks for two criteria:
        1. Whether there are more than four quadrants showing edema.
        2. Whether edema is present in the same quadrant across three consecutive layers.
        
        Args:
        - df (DataFrame): The SPARCC scoring DataFrame.
        - roi_start_layer (int): The start layer index for the region of interest.
        - roi_end_layer (int): The end layer index for the region of interest.
        
        Returns:
        - A string providing reasons for the active sacroiliitis diagnosis or stating that no significant findings were detected.
        """
        
        # Define the list of column names to check for edema presence
        col_list = ["iru", "sru", "ird", "srd", "slu", "ilu", "sld", "ild"]
        text1 = ""
        sum1 = 0
        
        # Loop through the DataFrame to check if the total number of edematous quadrants exceeds four
        for i in range(len(df)):
            sum1 += df.loc[i, col_list].sum()
            if sum1 >= 4:
                text1 += "有超过四个象限出现水肿。\n"
        text2 = ""
        edema_quadrant_layer = []
        
        # Loop through the DataFrame to find quadrants showing edema in three consecutive layers
        for i in range(len(df)-2):
            for col in col_list:
                # Check if edema is present in the same quadrant across three consecutive layers
                if df.loc[i, col] == 1 and df.loc[i+1, col] == 1 and df.loc[i+2, col] == 1:
                    edema_quadrant_layer.append({col: [i+roi_start_layer, i+1+roi_start_layer, i+2+roi_start_layer]})
        # Merge dictionaries for the same quadrant using the helper method
        edema_quadrant_layer = self.merge_dicts_with_same_keys(edema_quadrant_layer)
        
        # Construct the text if there are any quadrants with consecutive edema
        if len(edema_quadrant_layer) > 0:
            for key, value in edema_quadrant_layer.items():
                text2 += "——" + self.data_store.quadrand_dict[key] + "在第"
                for item in value:
                    text2 += "{}、".format(item)
                text2 = text2[:-1]
                text2 += "层连续出现水肿。\n"
        
        # If no significant edema findings, return a default message
        if text1 == "" and text2 == "":
            return "无超过四个象限的水肿或某一象限超过连续三层的水肿，不符合活动性骶髂关节炎的定义。\n"
        else:
            # Construct the final text combining both checks
            final_text = ""
            if text1 != "":
                final_text += text1
            if text2 != "":
                final_text += "连续三层水肿的象限：\n" + text2
        return final_text
    
    def get_active_sacroiliitis_text(self, active_sacroiliitis_res):
        """
        This method generates a conclusion text for the diagnosis of active sacroiliitis.
        
        Args:
        - active_sacroiliitis_res (int): A flag indicating whether active sacroiliitis was detected (1) or not (0).
        
        Returns:
        - A string stating whether the diagnosis meets the criteria for active sacroiliitis.
        """
        text = "活动性骶髂关节炎诊断结果："
        # Check the result flag and return the appropriate diagnosis conclusion
        if active_sacroiliitis_res:
            return text + "符合活动性骶髂关节炎的定义。\n"
        else:
            return text + "不符合活动性骶髂关节炎的定义。\n"
    
    def get_recommendation_prompt(self, content):
        """
        This method generates a prompt for the recommendation text based on the edema information.
        The prompt is intended to be used by a language model to provide a risk assessment and recommendation.
        
        Args:
        - content (str): The summarized edema information from the report.
        
        Returns:
        - A string prompt to be used for generating recommendations.
        """
        prompt = "你是一个风湿科的助理医生，需要你根据已有的水肿信息，判断患者患有强直性脊柱炎的概率和面对的风险，解释原因并给出建议，水肿信息如下：\n"+content
        return prompt
    
    def get_recommendation_text(self, content):
        """
        This method generates a recommendation text based on the edema information using a language model (Qwen).
        
        Args:
        - content (str): The input content for generating recommendations.
        
        Returns:
        - A string containing the generated recommendations from the language model.
        """
        # Generate the prompt using the helper method
        content = self.get_recommendation_prompt(content)
        # messages = [
        # {'role': 'user', 'content': content}]
        # response = Generation.call(
        #     'qwen-max',
        #     messages=messages,
        #     seed=5, 
        #     result_format='message',
        # )
        # full_content = response.output.choices[0]['message']['content']
        
        # for chunk in openai.ChatCompletion.create(
        #     model="Qwen",
        #     messages=[
        #         {"role": "user", "content":content }
        #     ],
        #     temperature=0.1,
        #     repetition_penalty=1.1,
        #     stream=True
        #     ):

        #     # if 'content' in chunk['choices'][0]['delta']:
        #     #     content1 = chunk['choices'][0]['delta']['content']
                
        #     #     yield str(f"data:{content1}\n\n")

        #     if hasattr(chunk.choices[0].delta, "content"):
        #         print(chunk.choices[0].delta.content, end="", flush=True)

        # Call the OpenAI language model API (Qwen) to generate a response
        response = openai.ChatCompletion.create(
            model="Qwen",
            messages=[
                {"role": "user", "content":content }
            ],
            temperature=0.1,
            repetition_penalty=1.1,
            stream=False
            )
        print('response.choices[0]')
        print(response.choices[0]['message']['content'])
        # Extract the generated text from the response
        full_content = response.choices[0]['message']['content']

        return full_content


    def clear_data_cache(self):
        """
        This method clears the cached data in the data store.
        It is useful for resetting the analysis state before processing a new dataset.
        """
        self.data_store.clear_cache()
        return
    
    def clear_model_cache(self):
        """
        This method is a placeholder for clearing any cached model data.
        Currently, no specific actions are performed here.
        """
        return