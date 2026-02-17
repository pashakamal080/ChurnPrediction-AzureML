import pandas as pd

# Load your sample input
df = pd.read_excel("samplerequestinput.xlsx")

print("from pydantic import BaseModel, Field")
print("\nclass CustomerData(BaseModel):")

# Map pandas dtypes to Pydantic types
dtype_mapping = {
    'int64': 'int',
    'float64': 'float',
    'object': 'str',
    'bool': 'bool'
}

for col, dtype in df.dtypes.items():
    # Get python type, default to str if unknown
    py_type = dtype_mapping.get(str(dtype), 'str')
    
    # Get a sample value for the swagger doc
    sample_val = df[col].iloc[0] if not df.empty else "value"
    if isinstance(sample_val, str):
        sample_val = f'"{sample_val}"'
        
    print(f"    {col}: {py_type} = Field(..., example={sample_val})")