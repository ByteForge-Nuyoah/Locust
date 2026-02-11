import argparse
import sys
import os
import json
import uncurl
from urllib.parse import urlparse
import re

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = str(value)
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '_', value)

def generate_locust_script(curl_command, output_file=None):
    try:
        # 使用 uncurl 解析 context
        # 注意：uncurl.parse_context 返回的是一个 Context 对象
        context = uncurl.parse_context(curl_command)
    except SystemExit:
        # Capture argparse SystemExit
        print("Error: uncurl internal argparse failed.")
        return
    except Exception as e:
        print(f"Error parsing curl command: {e}")
        return

    # 提取信息
    url = context.url
    method = context.method.lower() if context.method else "get"
    headers = context.headers
    data = context.data
    cookies = context.cookies
    
    # 解析 URL 获取 path 和 host
    parsed_url = urlparse(url)
    host = f"{parsed_url.scheme}://{parsed_url.netloc}"
    path = parsed_url.path
    if parsed_url.query:
        path += "?" + parsed_url.query

    # 生成类名和文件名
    endpoint_name = slugify(parsed_url.path.split('/')[-1] or 'root')
    class_name = "".join(x.title() for x in endpoint_name.split('_')) + "User"
    
    # 模板
    script_content = f"""from locust import task, HttpUser, constant_pacing
import json

class {class_name}(HttpUser):
    wait_time = constant_pacing(1)
    host = "{host}"

    def on_start(self):
        # 初始化 Headers
        self.client.headers.update({json.dumps(headers, indent=12)})
        
        # 初始化 Cookies (如果存在)
        # self.client.cookies.update({json.dumps(cookies, indent=12)})

    @task
    def generated_task(self):
        # URL: {url}
"""
    
    # 构建请求部分
    request_line = f'        with self.client.request("{method}", "{path}", catch_response=True'
    
    if data:
        # 尝试判断 data 是否为 JSON
        try:
            if isinstance(data, str):
                json_data = json.loads(data)
                request_line += f', json={json.dumps(json_data, indent=12)}'
            else:
                 request_line += f', data={repr(data)}'
        except:
             request_line += f', data=\'\'\'{data}\'\'\''
    
    request_line += ') as response:\n'
    request_line += '            if response.status_code >= 400:\n'
    request_line += f'                response.failure(f"Request failed with status {{response.status_code}}")'

    script_content += request_line

    # 输出
    if output_file:
        with open(output_file, 'w') as f:
            f.write(script_content)
        print(f"Successfully generated locust script: {output_file}")
    else:
        print(script_content)

def main():
    parser = argparse.ArgumentParser(description="Convert curl command to Locust script")
    parser.add_argument("inputs", nargs='+', help="Files containing curl command (searches projects/<project>/data/) or curl strings")
    parser.add_argument("-p", "--project", required=True, help="Project name (e.g., crm, website)")
    parser.add_argument("-o", "--output", help="Output directory or file path. If multiple inputs, must be a directory or omitted. (defaults to projects/<project>/scenarios/generated/)")
    
    args = parser.parse_args()
    
    # Determine default output directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Root
    default_output_dir = os.path.join(project_root, "projects", args.project, "scenarios", "generated")
    
    # Determine default data search path
    default_data_dir = os.path.join(project_root, "projects", args.project, "data")
    default_curl_dir = os.path.join(default_data_dir, "curl")
    
    for input_arg in args.inputs:
        # 1. Determine input file path
        input_path = input_arg
        if not os.path.exists(input_path):
            # Try searching in default_curl_dir (projects/<project>/data/curl)
            potential_path_curl = os.path.join(default_curl_dir, input_path)
            if os.path.exists(potential_path_curl):
                input_path = potential_path_curl
            else:
                # Try searching in default_data_dir (projects/<project>/data)
                potential_path = os.path.join(default_data_dir, input_path)
                if os.path.exists(potential_path):
                    input_path = potential_path
                else:
                    # Try searching in src/data/ (legacy fallback)
                    potential_path_global = os.path.join("src", "data", input_path)
                    if os.path.exists(potential_path_global):
                        input_path = potential_path_global
        
        curl_command = ""
        if os.path.exists(input_path):
            print(f"Processing file: {input_path}")
            with open(input_path, 'r') as f:
                curl_command = f.read().strip()
        else:
            # Assume it's a raw command string
            print(f"Processing raw curl string...")
            curl_command = input_arg

        # Clean up newlines and backslashes
        curl_command = curl_command.replace('\\\n', ' ').replace('\n', ' ')
        
        # 2. Determine output file path
        output_file = None
        
        # Try to parse context to get default name
        try:
            context = uncurl.parse_context(curl_command)
            parsed_url = urlparse(context.url)
            endpoint_name = slugify(parsed_url.path.split('/')[-1] or 'root')
            default_filename = f"{endpoint_name}.py"
        except:
            default_filename = "script.py"

        if args.output:
            if len(args.inputs) > 1:
                # If multiple inputs, output must be treated as directory
                # Check if it looks like a file (has extension)
                if os.path.splitext(args.output)[1]:
                    print(f"Warning: Multiple inputs provided but output '{args.output}' looks like a file. Using it as a directory.")
                    output_dir = args.output
                else:
                    output_dir = args.output
                
                output_file = os.path.join(output_dir, default_filename)
            else:
                # Single input
                if os.path.isdir(args.output) or args.output.endswith('/'):
                    output_file = os.path.join(args.output, default_filename)
                else:
                    output_file = args.output
        else:
             # Default path
             output_file = os.path.join(default_output_dir, default_filename)

        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            generate_locust_script(curl_command, output_file)
        except SystemExit:
            print("Error: uncurl failed to parse the command. Please ensure it is a valid curl command.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
