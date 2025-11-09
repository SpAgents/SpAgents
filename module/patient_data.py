import pandas as pd

class PatientData(object):
    """
    This class is responsible for storing and managing patient data.
    Patient data includes basic information, examination information, middle information, and result information.
    """
    def __init__(self, config):
        '''
        Initialize patient data.
        :param config: A dictionary containing patient data.
        '''
        # basic information
        self.patient_id = config.get("patient_id")
        self.name = config.get("patient_name")
        self.sex = config.get("sex")
        self.age = config.get("age")
        self.diagnosis_result_label = config.get("diagnosis_result_label")
        self.report_time = config.get("report_time")
        self.report_find = config.get("report_find")
        self.report_conclusion = config.get("report_conclusion")
        
        self.history_present_illness = config.get("history_present_illness")
        self.history_past_illness = config.get("history_past_illness")
        self.family_medical_history = config.get("family_medical_history")
        self.physical_examination = config.get("physical_examination")
        
        self.B27 = config.get("B27")
        
        self.CRP = config.get("CRP")
        self.ESR = config.get("ESR")
        
        self.t2_mri_path = config.get("t2_mri_path")
        #这个是sparcc的真实标签，做工具使用智能体与真实sparcc评分对比的实验时会用到：
        # self.sparcc_df = pd.read_csv("/data1/lzf/301agent/data/sparcc_label_df.csv")
    
    def __repr__(self):
        return (f"This is a PatientData of patient_id={self.patient_id}")

    def get_all_attributes(self):
        '''
        Return all attributes as a dictionary.
        '''
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def get_all_info(self):
        return {key:value for key, value in {
            "patient_id": self.patient_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            
            "report_time": self.report_time,
            "report_find": self.report_find,
            
            "history_present_illness": self.history_present_illness,
            "history_past_illness": self.history_past_illness,
            "family_medical_history": self.family_medical_history,
            "physical_examination": self.physical_examination,
            
            "B27": self.B27,

            "CRP": self.CRP,
            "ESR": self.ESR,
        }.items() if value is not None}
    
    def get_text(self):
        # 对应EX_clinical_1
        return {key:value for key, value in {
            "patient_id": self.patient_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            
            "history_present_illness": self.history_present_illness,
            "history_past_illness": self.history_past_illness,
            "family_medical_history": self.family_medical_history,
            "physical_examination": self.physical_examination,
            
        }.items() if value is not None}
    
    def get_text_b27(self):
        # 对应EX_clinical_2
        return {key:value for key, value in {
            "patient_id": self.patient_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            
            "history_present_illness": self.history_present_illness,
            "history_past_illness": self.history_past_illness,
            "family_medical_history": self.family_medical_history,
            "physical_examination": self.physical_examination,
            
            "B27": self.B27,
        }.items() if value is not None}
    
    def get_text_crp_esr(self):
        # 对应EX_clinical_3
        return {key:value for key, value in {
            "patient_id": self.patient_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            
            "history_present_illness": self.history_present_illness,
            "history_past_illness": self.history_past_illness,
            "family_medical_history": self.family_medical_history,
            "physical_examination": self.physical_examination,
            
            "CRP": self.CRP,
            "ESR": self.ESR,
        }.items() if value is not None}
    
    def get_text_b27_crp_esr(self):
        # 对应EX_clinical_4
        return {key:value for key, value in {
            "patient_id": self.patient_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            
            "history_present_illness": self.history_present_illness,
            "history_past_illness": self.history_past_illness,
            "family_medical_history": self.family_medical_history,
            "physical_examination": self.physical_examination,
            
            "B27": self.B27,

            "CRP": self.CRP,
            "ESR": self.ESR,
        }.items() if value is not None}

    def get_text_crp_esr_image(self):
        return {key:value for key, value in {
            "patient_id": self.patient_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            
            "report_time": self.report_time,
            "report_find": self.report_find,
            
            "history_present_illness": self.history_present_illness,
            "history_past_illness": self.history_past_illness,
            "family_medical_history": self.family_medical_history,
            "physical_examination": self.physical_examination,

            "CRP": self.CRP,
            "ESR": self.ESR,
        }.items() if value is not None}
    
    def get_sparcc_text_by_id(self, patient_id, sparcc_df):
        patient_rows = sparcc_df[sparcc_df["id"].str.contains(patient_id)]
        sparcc_total = patient_rows[["iru", "sru", "ird", "srd", "rdeep", "rinten", "slu", "ilu", "sld", "ild", "ldeep", "linten"]].sum(axis=1).sum()
        patient_rows = patient_rows.reset_index(drop=True)
        sparcc_text = patient_rows.to_string(index=False)
        text = "SPARCC评分表格,id列表示患者id和对应的层数：\n" + sparcc_text + "\nSPARCC总分：" + str(sparcc_total)
        return text

    def get_all_info_sparcc(self):
        sparcc_text = self.get_sparcc_text_by_id(self.patient_id, self.sparcc_df)
        
        return_dict = {key:value for key, value in {
            "patient_id": self.patient_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            
            "report_time": self.report_time,
            "report_find": self.report_find,
            
            "history_present_illness": self.history_present_illness,
            "history_past_illness": self.history_past_illness,
            "family_medical_history": self.family_medical_history,
            "physical_examination": self.physical_examination,
            
            "B27": self.B27,

            "CRP": self.CRP,
            "ESR": self.ESR,
            "sparcc": sparcc_text
        }.items() if value is not None}
        
        return return_dict


    def get_all_info_sparcc_without_image(self):
        sparcc_text = self.get_sparcc_text_by_id(self.patient_id, self.sparcc_df)
        
        return_dict = {key:value for key, value in {
            "patient_id": self.patient_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            
            "history_present_illness": self.history_present_illness,
            "history_past_illness": self.history_past_illness,
            "family_medical_history": self.family_medical_history,
            "physical_examination": self.physical_examination,
            
            "B27": self.B27,

            "CRP": self.CRP,
            "ESR": self.ESR,
            "sparcc": sparcc_text
        }.items() if value is not None}
        
        return return_dict

    def update_by_dict(self, updata_dict):
        '''
        Update the patient data by a dictionary.
        :param updata_dict: A dictionary containing the updated patient data.
        '''
        for key, value in updata_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"'Patient' object has no attribute '{key}'")
        
    
    def update_attribute(self, attr_name, value):
        '''
        Update the value of an attribute.
        :param attr_name: The name of the attribute.
        :param value: The value to be updated.
        '''
        if hasattr(self, attr_name):
            setattr(self, attr_name, value)
        else:
            raise AttributeError(f"'Patient' object has no attribute '{attr_name}'")

    def get_attribute(self, attr_name):
        '''
        Get the value of an attribute.
        :param attr_name: The name of the attribute.
        :return: The value of the attribute.
        '''
        if hasattr(self, attr_name):
            return getattr(self, attr_name)
        else:
            raise AttributeError(f"'Patient' object has no attribute '{attr_name}'")