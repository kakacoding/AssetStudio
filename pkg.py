# -*- en coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import csv
import json
import collections
from io import open
from os import path
from collections import OrderedDict
from enum import Enum, auto

MAX_ROWs_PRINTED = 100
#打印100K以上大尺寸资源
MAX_BIGSIZE_PRINTED = 1024*100

class DataType(Enum):
    Total = auto()
    FX = auto()
    Anim = auto()
    Char = auto()
    Scene = auto()
    UI = auto()
    TA = auto()
    Other = auto()

#报告页面中的分组
DataTypeDetailInfo = collections.OrderedDict()
DataTypeDetailInfo[DataType.Total] = '汇总'
DataTypeDetailInfo[DataType.FX] = '特效'
DataTypeDetailInfo[DataType.Anim] = '动画'
DataTypeDetailInfo[DataType.Char] = '角色'
DataTypeDetailInfo[DataType.Scene] = '场景'
DataTypeDetailInfo[DataType.UI] = 'UI'
DataTypeDetailInfo[DataType.TA] = 'TA'
DataTypeDetailInfo[DataType.Other] = '未分类'

#重复入包项中，根据分类需要忽略掉的内容
DuplicateNeedIgnoreTable={}
for t in DataType:
    DuplicateNeedIgnoreTable[t]=[]
DuplicateNeedIgnoreTable[DataType.Anim] = [
    #ingame和lobby重复的模型
    'SK_Char_Labula001_Body','SK_Char_Kazama001_Bag','SK_Char_KazamaE001_Bag',
    #动态骨骼导致
    'SK_Weap_VictorE001',
    #骨骼数量不同
    'SK_Weap_Jabali001','SK_Weap_Labula001',
    #双武器导致
    'SK_Weap_Custos001_W1','SK_Weap_Custos001_W2',
    #左右手特效挂点不同
    'SK_Weap_ZhongAiLi_GunE001_L','SK_Weap_ZhongAiLi_GunE001_R','SK_Weap_ZhongAiLi_Gun001_R_Lod1',
]
DuplicateNeedIgnoreTable[DataType.UI] = [
    #地图缩略图，暂时相同
    'bground_bg_002','bground_bg_008','bground_bg_016','bground_bg_020',
    #六边形背景
    'Img_SH_UIBGLine',
]
DuplicateNeedIgnoreTable[DataType.TA] = [
    #忽略urp相关
    'Large01','Large02','Medium01','Medium02','Medium03','Medium04','Medium05','Medium06','Thin01','Thin02'
]
DuplicateNeedIgnoreTable[DataType.Char] = [
    #双武器
    'SK_Weap_ZhongAiLi_Gun001_L_Lod1_Lod1','SK_Weap_ZhongAiLi_Gun001_R_Lod1_Lod1',
]

#经过筛选后需要显示在报告中的内容
DuplicateTable={}
UnCompressTable={}
BigTextureTable={}
BigAnimTable={}
BigMeshTable={}
MeshBytes={}
TextureBytes={}
AnimBytes={}
TextAssetsBytes={}

for t in DataType:
    DuplicateTable[t]=''
    UnCompressTable[t]=''
    BigTextureTable[t]=''
    BigAnimTable[t]=''
    BigMeshTable[t]=''
    MeshBytes[t]=0
    TextureBytes[t]=0
    AnimBytes[t]=0

#被筛掉的内容
DuplicateIgnoredTable=[]
UnCompressIgnoredTable=[]


if sys.version_info.major < 3:
    reload(sys)
    sys.setdefaultencoding('utf8')

markdeep_head = """
<head>
    <title>pkgdoctor</title>
    <meta charset="utf-8"> 
    <link rel="stylesheet" href="https://cdn.staticfile.org/twitter-bootstrap/3.3.7/css/bootstrap.min.css">
    <script src="https://cdn.staticfile.org/jquery/2.1.1/jquery.min.js"></script>
    <script src="https://cdn.staticfile.org/twitter-bootstrap/3.3.7/js/bootstrap.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>markdeepOptions={tocStyle:'none'}</script>
</head>
<body>
<style>
    body {font-family: "Helvetica Neue",Helvetica,Arial,sans-serif; font-size: 14px; color: #333; padding: 20px;}
    .md h1 {color: #ff6600; font-size: 20px; font-weight: bold; border-bottom: 3px solid;}
    .md div.title {background-color: #ff6600;}
    .md table th {color: #FFF; background-color: #AAA; border: 1px solid #888; padding: 8px 15px 8px 15px;}
    .md table {font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;font-size: 14px; border-collapse: collapse; line-height: 140%; page-break-inside: avoid;}
    .md table td {padding: 5px 15px 5px 15px; border: 1px solid #888; vertical-align: top; text-align: left; }
    .md table tr:nth-child(2n) {background: #EEE;}
    .md p {font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;font-size: 14px; margin: 0 0 10px;}
    .md {counter-reset: h1;}
    .md h1::before {content: counter(h1) " "; counter-increment: h1; margin-right: 10px; }
    .md img {border: solid #ddd 1px; max-width: 96px; background-color: #eee;}
</style>
<div class="md">
"""

def get_FileSize(filePath):
    fsize = path.getsize(filePath)
    fsize = fsize/float(1024*1024)
    return round(fsize,2)

def get_FolderSize(folderPath, fsize=0):
    for root, dirs, files in os.walk(folderPath):
        for f in files:
            fsize += os.path.getsize(os.path.join(root, f))
    return fsize
def pretty_number(num):
    if num < 1024:
        return str(num)
    if num < pow(1024,2):
        return "%.1fK" % (num/1024)
    if num < pow(1024,3):
        return "%.1fM" % (num/pow(1024,2))
    if num < pow(1024,4):
        return "%.2fG" % (num/pow(1024,3))
    return str(num)

def res2type(name, type, container, originalfile):
    lowerName = name.lower()
    lowerContainer = container.lower()
    if (lowerName.startswith('t_char') and type=='Texture2D') or ((lowerName.startswith('sk_') or lowerName.find('_char')!=-1 or lowerName.find('_body')!=-1 or lowerName.find('_wp')!=-1 or container.find('wp')!=-1) and type == 'Mesh'):
        return DataType.Char
    elif (name.startswith('T_Fx') and type=='Texture2D') or (lowerName.find('fx')!=-1 and type=='Mesh'):
        return DataType.FX
    elif type == 'AnimationClip' and (name.find('_UI_')==-1 and container.find('ui')==-1 and originalfile.find('ui')==-1) or ((container.find('@') != -1 or container.find('.playable') != -1) or originalfile.find('overrideController') != -1):
        return DataType.Anim
    elif (name.startswith('SK_') and container.find('@') == -1):
        return DataType.Anim
    elif (name.find('_UI_')!=-1 or name.startswith('UI_') or type=='Texture2D') or (type=='Shader' and container.find('.prefab') != -1) or (type == 'AnimationClip' and (container.find('.prefab') != -1 or container.find('.controller') != -1 or originalfile.find('ui')!=-1)):
        return DataType.UI
    elif ((name.startswith('T_Env') or name.find('Lightmap') != -1) and type == 'Texture2D') or (type == 'Mesh' and (lowerName.find('sm_prop')!=-1 or (container.find('.prefab') != -1 or originalfile.find('scene')!=-1))):
        return DataType.Scene
    elif (type == 'Shader' and container.find('prefab') == -1):
        return DataType.TA
    else:
        return DataType.Other
    
def processdata_bytype(dic, v, name, type, container, originalfile):
    dic[DataType.Total] += v
    container = container.lower()
    dic[res2type(name, type, container, originalfile)]+= v

def process_pkg_csv(tsvname):
    apkPath = tsvname[0:-12]+".apk"
    wwisePath = tsvname[0:-12]+"\\assets\\Audio"
    assets = {}
    dir_name = path.dirname(tsvname)

    pkg_html = path.join(dir_name,'pkg.html')
    markdown = open(pkg_html, 'w', encoding='utf-8')
    markdown.write(markdeep_head)
    # markdown.write('# %s/n' % (self.getUniqueName()))
    with open(tsvname, encoding='utf-8') as infile:
        if 'tsv' in tsvname:
            try:
                reader = csv.DictReader(infile, delimiter='\t')
            except:
                reader = csv.DictReader(infile, delimiter=b'\t')
        else:
            reader = csv.DictReader(infile)
        for row in reader:
            # print(row)
            hash = row['Hash']
            filename = row['FileName']
            if row['Container'].startswith('assets/'):
                row['Container'] = row['Container'][7:]
            # row['Container'] = row['Container'].replace(' ', '_')
            OriginalFile = row['OriginalFile']
            if OriginalFile.startswith('assets/'):
                OriginalFile = OriginalFile[7:]
            elif 'app/Data/' in OriginalFile:
                idx = OriginalFile.find('app/Data/')
                OriginalFile = OriginalFile[idx + 9:]
            row['OriginalFile'] = OriginalFile
            # row['OriginalFile'] = row['OriginalFile'].replace(' ', '_')
            if not hash:
                hash = row['Name']+row['Type']+row['Dimension']+row['Format']+row['Size']
            if filename:
                file_path = path.join(dir_name, filename)
                if path.exists(file_path):
                    file_size = path.getsize(file_path)
                    hash = row['Type'] + str(file_size)
            if hash not in assets:
                assets[hash] = {
                    'wasted': 0,
                    'items': []
                }
            asset_item = assets[hash]
            row['Size'] = int(row['Size'])
            asset_item['items'].append(row)
            asset_item['wasted'] = row['Size'] * (len(asset_item['items']) - 1) 
            if row['Type'] == 'Texture2D':
                TextureBytes[res2type(row['Name'], row['Type'], row['Container'], row['OriginalFile'])] += row['Size']
            if row['Type'] == 'Mesh':
                MeshBytes[res2type(row['Name'], row['Type'], row['Container'], row['OriginalFile'])] += row['Size']
            if row['Type'] == 'AnimationClip':
                AnimBytes[res2type(row['Name'], row['Type'], row['Container'], row['OriginalFile'])] += row['Size']
            if row['Type'] == 'TextAsset':
                extName = os.path.splitext(row['Name'])[1]
                if extName=='':
                    extName = os.path.splitext(row['Container'])[1]
                if extName =='':
                    extName=row['Name']
                if TextAssetsBytes.keys().__contains__(extName):
                    TextAssetsBytes[extName] += row['Size']
                else:
                    TextAssetsBytes[extName] = row['Size']
            # print(row['Name'], md5)

    total_bytes = 1
    total_texture_bytes = 0
    total_shader_bytes = 0
    total_font_bytes = 0
    total_mesh_bytes = 0
    total_audio_bytes = 0
    total_text_bytes = 0
    total_animation_bytes = 0

    # TODO: refactor
    total_wasted_bytes = 0
    total_wasted_texture_bytes = 0
    total_wasted_shader_bytes = 0
    total_wasted_font_bytes = 0
    total_wasted_mesh_bytes = 0
    total_wasted_audio_bytes = 0
    total_wasted_text_bytes = 0
    total_wasted_animation_bytes = 0

    total_uncompressed_bytes = 0
    total_uncompressed_count = 0
    for k, v in assets.items():
        wasted_bytes = v['wasted']
        total_wasted_bytes += wasted_bytes
        items = v['items']
        row = items[0]
        items_bytes = row['Size'] * len(items)
        total_bytes += items_bytes
        if row['Type'] == 'Texture2D':
            total_texture_bytes += items_bytes
            total_wasted_texture_bytes += wasted_bytes
        elif row['Type'] == 'Shader':
            total_shader_bytes += items_bytes
            total_wasted_shader_bytes += wasted_bytes
        elif row['Type'] == 'Font':
            total_font_bytes += items_bytes
            total_wasted_font_bytes += wasted_bytes
        elif row['Type'] == 'Mesh':
            total_mesh_bytes += items_bytes
            total_wasted_mesh_bytes += wasted_bytes
        elif row['Type'] == 'AudioClip':
            total_audio_bytes += items_bytes
            total_wasted_audio_bytes += wasted_bytes
        elif row['Type'] == 'AnimationClip':
            total_animation_bytes += items_bytes
            total_wasted_animation_bytes += wasted_bytes
        elif row['Type'] == 'TextAsset':
            total_text_bytes += items_bytes
            total_wasted_text_bytes += wasted_bytes

        if row['Type'] == 'Texture2D' and 'DXT' not in row['Format'] and 'BC' not in row['Format'] and 'TC' not in row['Format']:
            total_uncompressed_bytes += items_bytes
            total_uncompressed_count += len(items)

    markdown.write('>[点击查看最新分析结果(如无法显示，拷贝出错误信息中的网址后单独打开即可)](https://teamcity.t3.xd.com/project/T3_Development?projectTab=preport_project4___________#all-projects)\n')
    markdown.write('# 包体概览\n')
    markdown.write('分析源:\n\n`%s`\n\n' % path.basename(apkPath))
    markdown.write('- apk解压前: **%s**\n' % pretty_number(path.getsize(apkPath)))
    wwise_bytes=get_FolderSize(wwisePath)
    total_bytes+=wwise_bytes
    markdown.write('- 对 apk 解压后的现有资产尺寸: **%s**\n' % pretty_number(total_bytes))
    markdown.write('  - Texture: **%s** (%.2f%%)\n' % (pretty_number(total_texture_bytes), total_texture_bytes * 100 / total_bytes))
    OrderedTextureBytes = OrderedDict(sorted(TextureBytes.items(), key = lambda kv:(kv[1]), reverse=True))
    for t in OrderedTextureBytes.keys():
        if OrderedTextureBytes[t] != 0:
            markdown.write('    - %s: **%s** (%.2f%%)\n' % (t, pretty_number(OrderedTextureBytes[t] ), OrderedTextureBytes[t]  * 100 / total_texture_bytes))        
    markdown.write('  - Mesh: **%s** (%.2f%%)\n' % (pretty_number(total_mesh_bytes), total_mesh_bytes * 100 / total_bytes))
    OrderedMeshBytes = OrderedDict(sorted(MeshBytes.items(), key = lambda kv:(kv[1]), reverse=True))
    for t in OrderedMeshBytes.keys():
        if OrderedMeshBytes[t] != 0:
            markdown.write('    - %s: **%s** (%.2f%%)\n' % (t, pretty_number(OrderedMeshBytes[t] ), OrderedMeshBytes[t]  * 100 / total_mesh_bytes))
    markdown.write('  - AnimationClip: **%s** (%.2f%%)\n' % (pretty_number(total_animation_bytes), total_animation_bytes * 100 / total_bytes))
    OrderedAnimBytes = OrderedDict(sorted(AnimBytes.items(), key = lambda kv:(kv[1]), reverse=True))
    for t in OrderedAnimBytes.keys():
        if OrderedAnimBytes[t] != 0:
            markdown.write('    - %s: **%s** (%.2f%%)\n' % (t, pretty_number(OrderedAnimBytes[t] ), OrderedAnimBytes[t]  * 100 / total_animation_bytes))
    markdown.write('  - TextAsset: **%s** (%.2f%%)\n' % (pretty_number(total_text_bytes), total_text_bytes * 100 / total_bytes))
    OrderedTextAssetsBytes = OrderedDict(sorted(TextAssetsBytes.items(), key = lambda kv:(kv[1]), reverse=True))
    for t in OrderedTextAssetsBytes.keys():
        if OrderedTextAssetsBytes[t] != 0:
            markdown.write('    - %s: **%s** (%.2f%%)\n' % (t, pretty_number(OrderedTextAssetsBytes[t] ), OrderedTextAssetsBytes[t]  * 100 / total_text_bytes))
    markdown.write('  - Shader: **%s** (%.2f%%)\n' % (pretty_number(total_shader_bytes), total_shader_bytes * 100 / total_bytes))
    markdown.write('  - Font: **%s** (%.2f%%)\n' % (pretty_number(total_font_bytes), total_font_bytes * 100 / total_bytes))
    markdown.write('  - Wwise: **%s** (%.2f%%)\n' % (pretty_number(wwise_bytes), wwise_bytes * 100 / total_bytes))
    #markdown.write('  - AudioClip: **%s** (%.2f%%)\n' % (pretty_number(total_audio_bytes), total_audio_bytes * 100 / total_bytes))

    markdown.write('- 其中重复入包的资产，可减去 **%s**\n' % pretty_number(total_wasted_bytes))
    markdown.write('  - Texture: **%s** (%.2f%%)\n' % (pretty_number(total_wasted_texture_bytes), total_wasted_texture_bytes * 100 / total_wasted_bytes))
    markdown.write('  - Mesh: **%s** (%.2f%%)\n' % (pretty_number(total_wasted_mesh_bytes), total_wasted_mesh_bytes * 100 / total_wasted_bytes))
    markdown.write('  - AnimationClip: **%s** (%.2f%%)\n' % (pretty_number(total_wasted_animation_bytes), total_wasted_animation_bytes * 100 / total_wasted_bytes))
    markdown.write('  - TextAsset: **%s** (%.2f%%)\n' % (pretty_number(total_wasted_text_bytes), total_wasted_text_bytes * 100 / total_wasted_bytes))
    markdown.write('  - Shader: **%s** (%.2f%%)\n' % (pretty_number(total_wasted_shader_bytes), total_wasted_shader_bytes * 100 / total_wasted_bytes))
    markdown.write('  - Font: **%s** (%.2f%%)\n' % (pretty_number(total_wasted_font_bytes), total_wasted_font_bytes * 100 / total_wasted_bytes))
    #markdown.write('  - AudioClip: **%s** (%.2f%%)\n' % (pretty_number(total_wasted_audio_bytes), total_wasted_audio_bytes * 100 / total_wasted_bytes))

    markdown.write('- 其中未经压缩的贴图尺寸为 **%s** \n' % pretty_number(total_uncompressed_bytes))
    markdown.write('  - 若统一选用 `ASTC_RGB_4x4` 格式，可减去 **%s**\n' % pretty_number(total_uncompressed_bytes - total_uncompressed_bytes/3)) # sizeof(RGB24) / bpp(astc_4x4) = 24 / 8 = 3
    markdown.write('  - 若统一选用 `ASTC_RGB_6x6` 格式，可减去 **%s**\n' % pretty_number(total_uncompressed_bytes - total_uncompressed_bytes/6.74)) # sizeof(RGB24) / bpp(astc_6x6) = 24 / 3.56 = 6.74
    markdown.write('  - 若统一选用 `ASTC_RGB_8x8` 格式，可减去 **%s**\n' % pretty_number(total_uncompressed_bytes - total_uncompressed_bytes/12)) # sizeof(RGB24) / bpp(astc_8x8) = 24 / 2 = 12

    markdown.write('\n')

    #重复
    count = 0
    for k in OrderedDict(sorted(assets.items(), key=lambda item: item[1]['wasted'], reverse=True)):
        v = assets[k]
        items = v['items']
        item_count = len(items)
        if item_count <= 1:
            # skip non-duplicated assets
            continue

        row = items[0]
        names = []
        containers = []
        originalFiles = []
        wrapModes=[]
        filterModes=[]
        preview = ''
        for item in items:
            container = item['Container']
            if not container:
                container = '""'
            names.append(item['Name'])
            containers.append(container)
            originalFiles.append(item['OriginalFile'])
            wrapModes.append(item['WrapMode'])
            filterModes.append(item['FilterMode'])
        asset_filename = row['FileName']
        if 'png' in asset_filename:
            preview = '![](%s)' % asset_filename.replace('/\\','/')
        type = row['Type']
        if type == 'Texture2D':
            type = 'Texture'
        elif type == 'AnimatioClip':
            type = 'AnimClip'
        format = row['Format']
        if 'Crunched' in format:
            format = format.replace('Crunched', '')
        
        elem = '%s|%s|%s|%s|%s|%s|%s|%s|%s\n' % (
            '<br>'.join(names),
            '%s<br>%s%s' % (type, pretty_number(row['Size']), '*%d'% item_count if item_count > 1 else ''),
            '**%s**' % pretty_number(v['wasted']),
            '%s<br>%s' % (row['Dimension'], format),
            '<br>'.join(wrapModes),
            '<br>'.join(filterModes),
            preview,
            '<br>'.join(containers),
            '<br>'.join(originalFiles),
        )

        found = False
        for t in DataType:
            if len(DuplicateNeedIgnoreTable[t]) > 0:
                for ignore in DuplicateNeedIgnoreTable[t]:
                    if ignore in names:
                        found = True
                        DuplicateIgnoredTable.append(elem)
                        break
                if found == True:
                    break
        if found == True:
            continue

        #忽略特效的相同图片不同wrapmode
        if ''.join(names).find('T_Fx')!=-1 and (len(wrapModes) == len(set(wrapModes)) or len(filterModes) == len(set(filterModes))):
            DuplicateIgnoredTable.append(elem)
            continue
        
        processdata_bytype(DuplicateTable, elem, (' ').join(names), row['Type'], (' ').join(containers), (' ').join(originalFiles))
        #markdown.write(elem)
        count += 1

    #未压缩贴图
    count = 0
    for k in OrderedDict(sorted(assets.items(), key=lambda item: item[1]['items'][0]['Size'], reverse=True)):        
        v = assets[k]    
        items = v['items']
        item_count = len(items)
        row = items[0]
        if row['Type'] != 'Texture2D':
            continue
        format = row['Format']
        #增加忽略EAC图
        if 'DXT' in format or 'BC' in format or 'TC' in format or 'EAC' in format:
        # or 'Alpha8' in format:
            continue
        asset_name = row['Name']
        asset_filename = row['FileName']
        if 'xdsdk' in asset_name or 'taptap' in asset_name or 'UnityWatermark' in asset_name:
            # from SDK
            continue

        #忽略render-piplelines.core插件的内置图
        if asset_name in ['UIFoldoutClosed','UIFoldoutOpened','UICheckMark','UIElement8px','White1px']:
            continue

        #忽略urp相关
        if asset_name in ['Large01','SearchTex'] and row['OriginalFile']=='bin/Data/globalgamemanagers.assets':
            continue

        elem = '%s|%s|%s|%s|%s|%s|%s\n' % (
            row['Name'],
            '%s%s' % (pretty_number(row['Size']), '*%d'% item_count if item_count > 1 else ''),
            row['Dimension'],
            row['Format'],
            preview,
            row['Container'],
            row['OriginalFile'],
        )
        #忽略数据图
        if asset_name.startswith('T_Char', 0) and asset_name.endswith('VA', 0):
            preview = ''
            UnCompressIgnoredTable.append(elem)
            continue

        #忽略unity默认资源
        if row['OriginalFile']=="bin/Data/unity default resources" and row['Container']=="":
            continue
        
        if 'png' in asset_filename:
            preview = '![](%s)' % asset_filename.replace('/\\','/')
        else:
            preview = ''
        
        #markdown.write(elem)
        processdata_bytype(UnCompressTable, elem, row['Name'], row['Type'], row['Container'], row['OriginalFile'])

        count += 1
        if count > MAX_ROWs_PRINTED:
            break

    #大尺寸贴图
    count = 0
    for k in OrderedDict(sorted(assets.items(), key=lambda item: item[1]['items'][0]['Size'], reverse=True)):
        v = assets[k]    
        items = v['items']
        row = items[0]
        if row['Type'] != 'Texture2D':
            continue
        dimension = row['Dimension']
        if '1024' not in dimension and '2048' not in dimension and '4096' not in dimension:
            continue

        asset_name = row['Name']
        asset_filename = row['FileName']
        if '_1024' in asset_name or '_2048' in asset_name or 'sactx' in asset_name or 'lightmap' in asset_name.lower() or 'UnitySplash-cube' in asset_name:
            continue
        if 'png' in asset_filename:
            preview = '![](%s)' % asset_filename.replace('/\\','/')
        else:
            preview = ''
        
        elem = '%s|%s|%s|%s|%s|%s\n' % (
        row['Name'],
        pretty_number(row['Size']),
        row['Dimension'],
        row['Format'],
        preview,
        row['Container'],)
        #markdown.write(elem)
        processdata_bytype(BigTextureTable, elem, row['Name'], row['Type'], row['Container'], row['OriginalFile'])
        count += 1
        if count > MAX_ROWs_PRINTED:
            break
    #大尺寸动画
    count = 0
    for k in OrderedDict(sorted(assets.items(), key=lambda item: item[1]['items'][0]['Size'], reverse=True)):
        v = assets[k]    
        items = v['items']
        row = items[0]
        if row['Type'] != 'AnimationClip' or row['Size'] < MAX_BIGSIZE_PRINTED:
            continue
        
        elem = '%s|%s|%s|%s\n' % (
        row['Name'],
        pretty_number(row['Size']),
        row['Container'],
        row['OriginalFile'],)
        #markdown.write(elem)
        processdata_bytype(BigAnimTable, elem, row['Name'], row['Type'], row['Container'], row['OriginalFile'])
        count += 1

    #大尺寸模型
    count = 0
    for k in OrderedDict(sorted(assets.items(), key=lambda item: item[1]['items'][0]['Size'], reverse=True)):
        v = assets[k]    
        items = v['items']
        row = items[0]
        if row['Type'] != 'Mesh'  or row['Size'] < MAX_BIGSIZE_PRINTED:
            continue
        
        elem = '%s|%s|%s|%s\n' % (
        row['Name'],
        pretty_number(row['Size']),
        row['Container'],
        row['OriginalFile'],)
        #markdown.write(elem)
        processdata_bytype(BigMeshTable, elem, row['Name'], row['Type'], row['Container'], row['OriginalFile'])
        count += 1
        
    markdown.write('</div>\n')
    markdown.write('<ul id="myTab" class="nav nav-tabs">\n')

    i = 0
    for key, value in DataTypeDetailInfo.items():
        if i == 0:
            i+=1
            markdown.write('    <li class="active"><a href="#%s" data-toggle="tab">%s</a></li>\n' % (key.name, value))
        else:
            markdown.write('    <li><a href="#%s" data-toggle="tab">%s关注</a></li>\n' % (key.name, value))

    markdown.write('</ul>\n')
    markdown.write('<div id="myTabContent" class="tab-content">\n')

    i=0
    for key, value in DataTypeDetailInfo.items():
        if i==0:
            markdown.write('    <div class="tab-pane fade in active md" id="%s">\n' % (key.name))
        else:
            markdown.write('    <div class="tab-pane fade md" id="%s">\n' % (key.name))

        markdown.write('# 资源重复入包 Top 榜(%s)\n' % (value))
        if DuplicateTable[key] != "":
            markdown.write('Name栏中多行名字不同，表示不同文件的内容相同。`删除多余资源并重新指定引用`\n\n')
            markdown.write('Name栏中多行名字相同，需根据`包含该资源的文件`及`原始Bundle文件`列具体分析。\n\n')
            markdown.write('- 同名的不同文件。`前者删除多余资源并重新指定引用`\n')
            markdown.write('- 一个资源被打入了多份，需要修改制作流程\n')
            markdown.write('  1. `尽量不引用unity默认资源`\n')
            markdown.write('  1. `通过变体的方式处理一定要相同的资源`\n\n')
            markdown.write('***原则上该表需要清空***\n')
            markdown.write('Name|文件类型|浪费|Format|____________WrapMode____________|FilterMode|Preview|包含该资源的文件|原始Bundle文件\n')
            markdown.write('----|----|------|------|-------|-------|---------|------------|-------\n')
            markdown.write(DuplicateTable[key])
            markdown.write('\n')
        else:
            markdown.write('啥都没有，棒棒哒~😏\n')

        if i==0:
            markdown.write('# 已忽略资源重复入包 Top 榜(%s)\n' % (value))
            markdown.write('Name|文件类型|浪费|Format|____________WrapMode____________|FilterMode|Preview|包含该资源的文件|原始Bundle文件\n')
            markdown.write('----|----|------|------|-------|-------|---------|------------|-------\n')
            for ignore in DuplicateIgnoredTable:
                markdown.write(ignore)
            markdown.write('\n')

        markdown.write('# 未压缩贴图 Top 榜(%s)\n' % (value))
        if UnCompressTable[key] != "":
            markdown.write('需改为压缩格式，特殊的图片会逐步加入到忽略列表中。\n\n')
            markdown.write('***原则上该表需要清空***\n')
            markdown.write('Name|Size|Dimension|Format|Preview|包含该资源的文件|原始Bundle文件\n')
            markdown.write('----|----|---------|------|-------|---------|------------\n')
            markdown.write(UnCompressTable[key])
            markdown.write('\n')
        else:
            markdown.write('啥都没有，棒棒哒~😏\n')

        if i==0:
            markdown.write('# 已忽略未压缩贴图 Top 榜(%s)\n' % (value))
            markdown.write('Name|Size|Dimension|Format|Preview|包含该资源的文件|原始Bundle文件\n')
            markdown.write('----|----|---------|------|-------|---------|------------\n')
            for ignore in UnCompressIgnoredTable:
                markdown.write(ignore)
            markdown.write('\n')

        markdown.write('# 大尺寸贴图 Top 榜(%s)\n' % (value))
        if BigTextureTable[key] != "":
            markdown.write('看是否有规格异常资源。比如`分辨率过大，压缩率不够，Size异常`\n\n')
            markdown.write('***此表常驻，每周一撸***\n')
            markdown.write('Name|Size|Dimension|Format|Preview|Container\n')
            markdown.write('----|----|---------|------|-------|---------\n')
            markdown.write(BigTextureTable[key])
            markdown.write('\n')
        else:
            markdown.write('啥都没有，棒棒哒~😏\n')

        markdown.write('# 大于 %s 动画 Top 榜(%s)\n' % (pretty_number(MAX_BIGSIZE_PRINTED), value))
        if BigAnimTable[key] != "":
            markdown.write('看是否有规格异常资源。比如`Size异常`\n\n')
            markdown.write('***此表常驻，每周一撸***\n')
            markdown.write('Name|Size|包含该资源的文件|原始Bundle文件\n')
            markdown.write('----|----|---------|------------\n')
            markdown.write(BigAnimTable[key])
            markdown.write('\n')
        else:
            markdown.write('啥都没有，棒棒哒~😏\n')

        markdown.write('# 大于 %s 模型 Top 榜(%s)\n' % (pretty_number(MAX_BIGSIZE_PRINTED), value))
        if BigMeshTable[key] != "":
            markdown.write('看是否有规格异常资源。比如`Size异常`\n\n')
            markdown.write('***此表常驻，每周一撸***\n')
            markdown.write('Name|Size|包含该资源的文件|原始Bundle文件\n')
            markdown.write('----|----|---------|------------\n')
            markdown.write(BigMeshTable[key])
            markdown.write('\n')
        else:
            markdown.write('啥都没有，棒棒哒~😏\n')

        markdown.write('    </div>\n')
        i+=1
    
    markdown.write('</div>\n')
    sc = """
<script>
var md = document.getElementsByClassName("md");
for(var i=0; i<md.length; i++){
    var element = md[i];
    element.innerHTML = marked.parse(element.innerHTML);
}
</script>
    """
    markdown.write(sc)
    markdown.write('</body>\n')
    print('\nreport -> %s\n' % pkg_html)

#--------------- big bundle.html start-------------------------------
markdeep_head_bigbundle = """
<head>
    <title>pkgdoctor</title>
    <meta charset="utf-8"> 
    <link rel="stylesheet" href="https://cdn.staticfile.org/twitter-bootstrap/3.3.7/css/bootstrap.min.css">
    <script src="https://cdn.staticfile.org/jquery/2.1.1/jquery.min.js"></script>
    <script src="https://cdn.staticfile.org/twitter-bootstrap/3.3.7/js/bootstrap.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>markdeepOptions={tocStyle:'none'}</script>
</head>
<body>
<style>
    body {font-family: "Helvetica Neue",Helvetica,Arial,sans-serif; font-size: 14px; color: #333; padding: 20px;}
    .md h1 {color: #ff6600; font-size: 20px; font-weight: bold; border-bottom: 3px solid;}
    .md div.title {background-color: #ff6600;}
    .md table th {color: #FFF; background-color: #AAA; border: 1px solid #888; padding: 8px 15px 8px 15px;}
    .md table {font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;font-size: 14px; border-collapse: collapse; line-height: 140%; page-break-inside: avoid;}
    .md table td {padding: 5px 15px 5px 15px; border: 1px solid #888; vertical-align: top; text-align: left; }
    .md table tr:nth-child(2n) {background: #EEE;}
    .md p {font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;font-size: 14px; margin: 0 0 10px;}
    .md {counter-reset: h1;}
    .md h1::before {content: counter(h1) " "; counter-increment: h1; margin-right: 10px; }
    .md img {border: solid #ddd 1px; max-width: 96px; background-color: #eee;}
</style>
<div class="md">
"""
def generate_big_bundle_html(tsvname):
    bundlePath = path.join(tsvname[0:-12], "assets/aa/Android")
    bigBundleList = {}
    for bundleFileName in os.listdir(bundlePath):
        filePath = path.join(bundlePath, bundleFileName)
        bundleSize = get_FileSize(filePath)
        if bundleSize > 5:
            bigBundleList[bundleFileName] = bundleSize
            # print(bundleFileName)

    dir_name = path.dirname(tsvname)
    pkg_html = path.join(dir_name,'big_bundle.html')

    markdown = open(pkg_html, 'w', encoding='utf-8')
    markdown.write(markdeep_head_bigbundle)
    markdown.write('# 大小异常的bundle列表\n')
    if len(bigBundleList.keys()) > 0:
        markdown.write('因为目前zstd是内存解压bundle，需要关注bundle大小。\n大小异常的定义：`（size 大于 5MB）`\n\n')
        markdown.write('Name|Size\n')
        markdown.write('----|----\n')
        for bundleName, size in bigBundleList.items():
            elem = '%s|%s\n' % (bundleName, "%.1fM" % size)
            markdown.write(elem)
        markdown.write('')
        markdown.write('\n')
    else:
        markdown.write('bundle大小无异常~😏\n')

    markdown.write('</div>\n')
    sc = """
<script>
var md = document.getElementsByClassName("md");
for(var i=0; i<md.length; i++){
    var element = md[i];
    element.innerHTML = marked.parse(element.innerHTML);
}
</script>
    """
    markdown.write(sc)    
    markdown.write('</body>\n')

#--------------- big bundle.html end-------------------------------

if __name__ == '__main__':
    #pkg_csv = "E:\hubin_t3_scrum\T3_Tools\pkg-doctor\Development_202307260904_[0.0.1695986_1695986][0.0.1695986]_appstore-pkg\pkg.tsv"
    if len(sys.argv) > 1:
        pkg_csv = sys.argv[1]    
    process_pkg_csv(pkg_csv)
    #generate_big_bundle_html(pkg_csv)