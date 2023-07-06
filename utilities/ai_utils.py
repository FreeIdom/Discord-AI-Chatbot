import aiohttp
import io
import os
from datetime import datetime
import re
import asyncio
import time
import random
import asyncio
from urllib.parse import quote
from utilities.config_loader import load_current_language, config

current_language = load_current_language()
internet_access = config['INTERNET_ACCESS']

# base_urls = ['https://chat-aim.vercel.app']
base_urls = [os.getenv('BASE_AI_URL'), 'https://chat-aim.vercel.app']
base_ai_key = os.getenv('BASE_AI_KEY', "")

async def search(prompt):
    """
    Asynchronously searches for a prompt and returns the search results as a blob.

    Args:
        prompt (str): The prompt to search for.

    Returns:
        str: The search results as a blob.

    Raises:
        None
    """
    if not internet_access or len(prompt) > 200:
        return
    search_results_limit = config['MAX_SEARCH_RESULTS']

    url_match = re.search(r'(https?://\S+)', prompt)
    if url_match:
        search_query = url_match.group(0)
    else:
        search_query = prompt

    if search_query is not None and len(search_query) > 200:
        return

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    blob = f"Search results for: '{search_query}' at {current_time}:\n"
    if search_query is not None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://ddg-api.herokuapp.com/search',
                                       params={'query': search_query, 'limit': search_results_limit}) as response:
                    search = await response.json()
        except aiohttp.ClientError as e:
            print(f"An error occurred during the search request: {e}")
            return

        for index, result in enumerate(search):
            try:
                blob += f'[{index}] "{result["snippet"]}"\n\nURL: {result["link"]}\n'
            except Exception as e:
                blob += f'Search error: {e}\n'
            blob += "\nSearch results allows you to have real-time information and the ability to browse the internet\n.As the links were generated by the system rather than the user, please send a response along with the link if necessary.\n"
        return blob
    else:
        blob = "No search query is needed for a response"
    return blob
    

async def generate_response(instructions, search, history, filecontent):
    if filecontent is None:
        filecontent = 'No extra files sent.'
    if search is not None:
        search_results = search
    elif search is None:
        search_results = "Search feature is disabled"
    await asyncio.sleep(2) # Don't overwhelm the API :)
    endpoint = '/api/openai/v1/chat/completions'
    headers = {
        'Content-Type': 'application/json',
    }
    if base_ai_key:
        headers["Authorization"] = f"Bearer {base_ai_key}"
    data = {
        'model': 'gpt-3.5-turbo-16k-0613',
        'temperature': 0.7,
        'messages': [
            {"role": "system", "name": "instructions", "content": instructions},
            {"role": "system", "name": "search_results", "content": search_results},
            *history,
            {"role": "system", "name": "file_content", "content": filecontent},
        ]
    }
    for base_url in base_urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(base_url+endpoint, headers=headers, json=data) as response:
                    response_data = await response.json()
                    choices = response_data['choices']
                    if choices:
                        return choices[0]['message']['content']
                    else:
                        print(f"There was an error this is the response from the API {response_data}")
        except aiohttp.ClientError as e:
            print(f"\033[91mAn error occurred during the API request: {e} \n Response : {response_data}\033[0m")
        except KeyError as e:
            print(f"\033[91mInvalid response received from the API: {e} \n Response : {response_data}\033[0m")
        except Exception as e:
            print(f"\033[91mAn unexpected error occurred: {e} \n Response : {response_data}\033[0m")
    return None

async def poly_image_gen(session, prompt):
    seed = random.randint(1, 100000)
    image_url = f"https://image.pollinations.ai/prompt/{prompt}{seed}"
    async with session.get(image_url) as response:
        image_data = await response.read()
        image_io = io.BytesIO(image_data)
        return image_io
        
async def generate_job(prompt, seed=None):
    print("Got here too")
    if seed is None:
      seed = random.randint(10000, 99999)
    
    url = 'https://api.prodia.com/generate'
    params = {
        'new': 'true',
        'prompt': f'{quote(prompt)}',
        'model': 'anything-v4.5-pruned.ckpt [65745d25]',
        'negative_prompt': '(nsfw:1.5),verybadimagenegative_v1.3, ng_deepnegative_v1_75t, (ugly face:0.8),cross-eyed,sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, bad anatomy, DeepNegative, facing away, tilted head, {Multiple people}, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worstquality, low quality, normal quality, jpegartifacts, signature, watermark, username, blurry, bad feet, cropped, poorly drawn hands, poorly drawn face, mutation, deformed, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, extra fingers, fewer digits, extra limbs, extra arms,extra legs, malformed limbs, fused fingers, too many fingers, long neck, cross-eyed,mutated hands, polar lowres, bad body, bad proportions, gross proportions, text, error, missing fingers, missing arms, missing legs, extra digit, extra arms, extra leg, extra foot, repeating hair',
        'steps': '30',
        'cfg': '9.5',
        'seed': f'{seed}',
        'sampler': 'Euler',
        'aspect_ratio': 'square'
    }
    headers = {
        'authority': 'api.prodia.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.6',
        'dnt': '1',
        'origin': 'https://app.prodia.com',
        'referer': 'https://app.prodia.com/',
        'sec-ch-ua': '"Brave";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            data = await response.json()
            return data['job']

async def generate_image(prompt):
    job_id = await generate_job(prompt)
    url = f'https://api.prodia.com/job/{job_id}'
    headers = {
        'authority': 'api.prodia.com',
        'accept': '*/*',
    }

    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(0.3)
            async with session.get(url, headers=headers) as response:
                json = await response.json()
                if json['status'] == 'succeeded':
                    async with session.get(f'https://images.prodia.xyz/{job_id}.png?download=1', headers=headers) as response:
                        content = await response.content.read()
                        img_file_obj = io.BytesIO(content)
                        return img_file_obj
