import ast
import base64
import itertools
import os
from flask_cors import CORS
from flask import Flask, request, jsonify,render_template
from werkzeug.utils import secure_filename
from towhee import AutoPipes, AutoConfig
from towhee.datacollection import DataCollection
import numpy as np
from transformers import AutoFeatureExtractor, AutoModel
import torchvision.transforms as T
from PIL import Image
import torch 
import warnings
from pymilvus import Collection, utility,MilvusClient
from pymilvus import connections,AnnSearchRequest,WeightedRanker
from milvus_model.hybrid import BGEM3EmbeddingFunction
# from pymilvus import model

# 配置
app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = os.getcwd()+'/uploads'  # 文件上传目录
VIDEO_ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv'}  # 支持的文件类型
PICTURE_ALLOWED_EXTENSIONS = {'png', 'jpg','jpeg'}  # 支持的文件类型
TXT_ALLOWED_EXTENSIONS = {'txt'}  # 支持的文件类型
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 限制最大文件为100MB
warnings.filterwarnings("ignore", category=FutureWarning)
model_ckpt = "/data/data/sunye/250107_milvus_api/vit-base-beans"
# model_ckpt = '/data/nas/8800/sunye/240914_image_similarity/vit-base-patch8-224'
# processor = AutoImageProcessor.from_pretrained(model_ckpt)
# model = AutoModel.from_pretrained(model_ckpt)

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com' 

# 加载预训练模型
extractor = AutoFeatureExtractor.from_pretrained(model_ckpt)
pic_model = AutoModel.from_pretrained(model_ckpt)
pic_model = pic_model.eval()
hidden_dim = pic_model.config.hidden_size
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
pic_model = pic_model.to(device)  # 将模型转移到 GPU 上

# processor = AutoImageProcessor.from_pretrained(model_ckpt)
# model = AutoModel.from_pretrained(model_ckpt)
# Data transformation chain.

# Images are resized/rescaled to the same resolution (224x224) 
transformation_chain = T.Compose(
    [
        # We first resize the input image to 256x256 and then we take center crop.
        T.Resize(int((256 / 224) * extractor.size["height"])),
        T.CenterCrop(extractor.size["height"]),
        T.ToTensor(),
        T.Normalize(mean=extractor.image_mean, std=extractor.image_std),
    ]
)

# 检查文件扩展名
def txt_allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in TXT_ALLOWED_EXTENSIONS
# 检查文件扩展名
def video_allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VIDEO_ALLOWED_EXTENSIONS
# 检查文件扩展名
def pic_allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')
# 上传文本的路由
@app.route('/extupload', methods=['POST'])
def extupload():
    text = request.form.get('text','强拆')
    score = request.form.get('socre','0.2')
    search_type = request.form.get('choice','hybrid')
    topk = request.form.get('topk','3')
    print(text)
    print(f'topk:{topk}')

    if not text:
        return jsonify({"error": "No input text"}), 400
    
    else:
        print(f"Searching for: {text}")
        print(f"Searching choice: {search_type}")
        ef = BGEM3EmbeddingFunction(use_fp16=False, device="cuda")
        dense_dim = ef.dim["dense"]
        print(dense_dim)
        query_embeddings = ef([text])  # 获取查询的嵌入表示
        
        connections.connect(uri = "http://10.56.6.22:19530")
        col = Collection("hybrid_demo")
        col.load()  # 加载集合到内存中
        
        if search_type == "dense":
            search_results = dense_search(col, query_embeddings["dense"][0],int(topk))
            print("Dense search results:")

        elif search_type == "sparse":
            search_results = sparse_search(col, query_embeddings["sparse"][0],int(topk))
            print("Sparse search results:")

        elif search_type == "hybrid":
            search_results = hybrid_search(
                col,
                query_embeddings["dense"][0],
                query_embeddings["sparse"][0],
                sparse_weight=0.7,
                dense_weight=1.0,
                topk=int(topk)
            )
            print("Hybrid search results:")
        
        # 处理搜索结果
        result_txt = []
        similarity = []
        for hit in search_results:
                print(hit)
                segment_score = hit['distance']
                text = hit["text"]
                # print(segment_score)
                # print(text)
                if(segment_score > float(score)):
                    similarity.append(segment_score)
                    result_txt.append(text)

        # 将2个列表打包成元组
        zipped_lists = list(zip(similarity, result_txt))
        # 按照 list1 降序排序
        sorted_zipped_lists = sorted(zipped_lists, key=lambda x: x[0], reverse=True)

        # 将排序后的结果拆解回原始的2个列表
        if sorted_zipped_lists:
            list1_sorted, list2_sorted = zip(*sorted_zipped_lists)
        else:
            list1_sorted, list2_sorted = [], []

        # 将结果转换回列表
        similarity = list(list1_sorted)
        result_txt = list(list2_sorted)   
        
        # 将3个列表按顺序合并
        result = [{"id": idx + 1, "text": text, "segment_score": segment_score} 
                for idx, (text, segment_score) in enumerate(zip(result_txt, similarity))]
        print(result)
        # 返回响应
        return jsonify({
            "message": "File uploaded successfully",
            "result": result
        }), 200     
    
# 上传图片的路由
@app.route('/picupload', methods=['POST'])
def picupload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    score = request.form.get('score','0.5')
    topk = request.form.get('topk','5')
    print(f'topk:{topk}')

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and pic_allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        # print(app.config['UPLOAD_FOLDER'])

        # 保存文件到指定路径
        file.save(filepath)

        # 打印文件路径到控制台
        print(f"File uploaded successfully. File path: {filepath}")

        search_results = picture_search(filepath,int(topk))
        
        # 处理搜索结果
        result_picture = []
        similarity = []
        for result in search_results:
            print(result)
            for hit in result:
                segment_score = hit["distance"]
                image_name = hit["entity"]["image_names"]
                print(segment_score)
                image_name="/data/data/sunye/250107_milvus_api/0311_2000_raw_processed_pictures/"+image_name
                print(image_name)
                if(segment_score > float(score)):
                    similarity.append(segment_score)
                    result_picture.append(image_name)
        # 将2个列表打包成元组
        zipped_lists = list(zip(similarity, result_picture))
        # 按照 list1 降序排序
        sorted_zipped_lists = sorted(zipped_lists, key=lambda x: x[0], reverse=True)

        # 将排序后的结果拆解回原始的2个列表
        if sorted_zipped_lists:
            list1_sorted, list2_sorted = zip(*sorted_zipped_lists)
        else:
            list1_sorted, list2_sorted = [], []

        # 将结果转换回列表
        similarity = list(list1_sorted)
        result_picture = list(list2_sorted)   
        image_base64_list = []
        for image_path in result_picture:
            # 将picture转换为Base64格式
            image_base64 = to_base64(image_path)
            image_type = "image/jpg"
            data_url = f"data:{image_type};base64,{image_base64}"
            if image_base64:
                image_base64_list.append(data_url)
            else:
                image_base64_list.append('null')
        # 将3个列表按顺序合并
        result = [{"id": idx + 1, "candidate_image": candidate_picture, "segment_score": segment_score,'image_base64':image_base64} 
                for idx, (candidate_picture, segment_score, image_base64) in enumerate(zip(result_picture, similarity, image_base64_list))]
        # 返回响应
        return jsonify({
            "message": "File uploaded successfully",
            "result": result
        }), 200     
    else:
        return jsonify({"error": "Invalid file type"}), 400
    
@app.route('/videoupload', methods=['POST'])
# 上传视频的路由
def videoupload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    score = request.form.get('score','0')
    topk = request.form.get('topk','5')

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and video_allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # 保存文件到指定路径
        file.save(filepath)

        # 打印文件路径到控制台
        print(f"File uploaded successfully. File path: {filepath}")

        result = video_search(filepath,int(topk),float(score))
        dc = DataCollection(result)
        #  使用 sorted() 进行降序排序
        sorted_data = sorted(dc, key=lambda x: x['segment_score'], reverse=True)
        candidate_video = [item['candidates'] for item in sorted_data]
        similar_segment = [item['similar_segment'] for item in sorted_data]
        segment_score = [item['segment_score'] for item in sorted_data]
        # 使用 sorted 对每个子列表进行降序排序
        sorted_segment_score = [sorted(sublist, reverse=True) for sublist in segment_score]
        # 使用sorted()排序
        # 将三个列表打包成元组
        zipped_lists = list(zip(candidate_video, similar_segment, sorted_segment_score))
        # 使用列表推导式，过滤掉包含空值的行
        sorted_zipped_lists = [row for row in zipped_lists if all(value not in (None, '', []) for value in row)]
        # 按照 list3 降序排序
        sorted_zipped_lists = sorted(sorted_zipped_lists, key=lambda x: x[2][0], reverse=True)

        # 将排序后的结果拆解回原始的三个列表
        if sorted_zipped_lists:
            list1_sorted, list2_sorted, list3_sorted = zip(*sorted_zipped_lists)
        else:
            list1_sorted, list2_sorted, list3_sorted = [], [], [] 

        # 将结果转换回列表
        candidate_video = list(list1_sorted)
        similar_segment = list(list2_sorted)
        segment_score = list(list3_sorted)
        segment_score = [row[0] for row in segment_score]
        print('candidate_video:',candidate_video)
        print('segment_score:',segment_score)
        dc.show()
        video_base64_list = []
        for video_path in candidate_video:
            # 将视频转换为Base64格式
            video_base64 = to_base64("/data/data/sunye/241017_milvus_video_similarity/test1/"+video_path)
            video_type = "video/mp4"
            data_url = f"data:{video_type};base64,{video_base64}"
            if video_base64:
                video_base64_list.append(data_url)
            else:
                video_base64_list.append('null')
        # 将3个列表按顺序合并
        result = [{"id": idx + 1, "candidate_video": candidate_video, "segment_score": segment_score,'video_base64':video_base64} 
                for idx, (candidate_video, segment_score, video_base64) in enumerate(zip(candidate_video, segment_score,video_base64_list))]
        # 返回响应
        return jsonify({
            "message": "File uploaded successfully",
            "result": result
        }), 200
    else:
        return jsonify({"error": "Invalid file type"}), 400

def to_base64(video_path):
    """将文件转换为Base64格式"""
    try:
        with open(video_path, "rb") as video_file:
            encoded_string = base64.b64encode(video_file.read()).decode("utf-8")
        return encoded_string
    except FileNotFoundError:
        return None
    
def video_search(search_video,topk,score):     
    search_conf = AutoConfig.load_config('video_copy_detection')
    search_conf.collection='video_embedding'
    search_conf.start_time = None
    search_conf.end_time = None
    search_conf.top_k = topk
    search_conf.device = 0 # 0 gpu -1 cpu
    search_conf.threshold = score #阈值
    search_conf.milvus_host = '10.56.6.22'
    # use leveldb
    search_conf.leveldb_path = '/data/data/sunye/250107_milvus_api/video_vec.db' 
    print(search_conf)
    # search_conf.hbase_table='video_copy_detection'
    search_pipe = AutoPipes.pipeline('video_copy_detection', search_conf)

    print('search_video:',search_video)
    result = search_pipe(search_video)
    return result

# 向量化 输入的是images数组
def pp(images):
    # device = model.device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # `transformation_chain` is a compostion of preprocessing
    # transformations we apply to the input images to prepare them
    # for the model. For more details, check out the accompanying Colab Notebook.
    # print(images)
    image_batch_transformed = torch.stack(
          [transformation_chain(Image.open(image_path).convert('RGB')) for image_path in images]
    )
    new_batch = {"pixel_values": image_batch_transformed.to(device)}
    with torch.no_grad():
        embeddings = pic_model(**new_batch).last_hidden_state[:, 0].cpu()
    return embeddings

    
def picture_search(search_picture,topk):     
    query_embedding = pp([search_picture])
        # combined = list(zip(query_embedding, query_img))
        
    print("查询图片：",search_picture)
    #在milvus进行查询
        
    client = MilvusClient(
        uri="http://10.56.6.22:19530"
    )
    # 确认连接是否成功
    if connections.has_connection("default"):
        print("Connected to Milvus server successfully!")
    else:
        print("Failed to connect to Milvus server.")

    print(topk)
    print(type(topk))
    search_results = client.search(
        "picture_test",
        data=query_embedding.tolist(),
        anns_field="feature_vectors",  # 字段名
        output_fields=["image_names"],
        limit=topk
    )
    return search_results

def dense_search(col, query_dense_embedding, topk):
    search_params = {"metric_type": "IP", "params": {}}
    # 查询时指定返回字段：id, text, distance
    res = col.search(
        [query_dense_embedding],
        anns_field="dense_vector",
        limit=topk,
        output_fields=["pk", "text"],  # 输出需要的字段
        param=search_params,
    )[0]
    # return [hit.get("text") for hit in res]
    return [
        {
            "id": hit.pk,
            "text": hit.get("text"),
            "distance": round(hit.distance, 4),
        }
        for hit in res
    ]

def sparse_search(col, query_sparse_embedding, topk):
    search_params = {
        "metric_type": "IP",
        "params": {},
    }
    res = col.search(
        [query_sparse_embedding],
        anns_field="sparse_vector",
        limit=topk,
        output_fields=["pk", "text"],
        param=search_params,
    )[0]
    return [
        {
            "id": hit.pk,
            "text": hit.get("text"),
            "distance": round(hit.distance, 4),
        }
        for hit in res
    ]

def hybrid_search(
    col,
    query_dense_embedding,
    query_sparse_embedding,
    sparse_weight=1.0,
    dense_weight=1.0,
    topk=5,
):
    dense_search_params = {"metric_type": "IP", "params": {}}
    dense_req = AnnSearchRequest(
        [query_dense_embedding], "dense_vector", dense_search_params, limit=topk
    )
    sparse_search_params = {"metric_type": "IP", "params": {}}
    sparse_req = AnnSearchRequest(
        [query_sparse_embedding], "sparse_vector", sparse_search_params, limit=topk
    )
    rerank = WeightedRanker(sparse_weight, dense_weight)
    res = col.hybrid_search(
        [sparse_req, dense_req], rerank=rerank, limit=topk, output_fields=["pk", "text"]
    )[0]
    return [
        {
            "id": hit.pk,
            "text": hit.get("text"),
            "distance": round(hit.distance, 4),
        }
        for hit in res
    ]


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8890,debug=True)
