import clr
clr.AddReference("System")
clr.AddReference("System.IO")
from System import IO
from System.Net import HttpWebRequest, WebResponse

def get_request(url):
    request = HttpWebRequest.Create(url)
    request.Method = "GET"
    
    response = request.GetResponse()
    response_stream = response.GetResponseStream()
    
    reader = IO.StreamReader(response_stream)
    response_text = reader.ReadToEnd()
    
    reader.Close()
    response.Close()
    
    return response_text

url = "http://127.0.0.1:5000/altitude"
response_text = get_request(url)
print(response_text)