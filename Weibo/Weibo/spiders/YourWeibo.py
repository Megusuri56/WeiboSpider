import sys
sys.path.append(r"")    #这里填入整个文件夹的绝对路径
import re
import scrapy
from Weibo.items import ImageItem
import os

class YourWeibo(scrapy.Spider):
    name = "YourWeibo"
    uid = ""    #这里填入需要保存的微博账号的uid
    start_page = 1    #开始保存的页码（从1开始，以https://weibo.cn/u/ + uid的显示为准）
    end_page = 1    #结束保存的页码（包含在内）
    weibos_in_file = 50    #一个文件内存放的微博条数
    only_original = False    #是否只保存原创微博
    all_HD_pic = False    #是否保存全部图片且为高清
    seperator = "<span>————————————————————</span>"   #分隔两条微博的分隔符（可自选）
    cookies = {}    #填入你自己的cookie（以https://weibo.cn为准)
    
    start_urls = [r"https://weibo.cn/" + uid + r"/profile"]    
    weibos = dict()
    
    def start_requests(self):
        for i in range(self.start_page,self.end_page+1):    #拼接url
            if self.only_original:
                url = self.start_urls[0] + "?filter=1&page=" + str(i)
            else:
                url = self.start_urls[0] + "?page=" + str(i)
            yield scrapy.Request(url, cookies=self.cookies)
        
    def saveFiles(self,response):
        title = ""
        if "comment" in response.url:
            title = response.css("span.ct::text").get()    #获取时间作为文件名
        if title == None:
            title = "default_title"
        title = title.strip()
        filename = f"{title}.html"
        filename = re.sub(r'[\/\\\:\*\?\"\<\>\|]','_',filename)
        
        post_content = ""
        if "/mblog/picAll/" in response.url:
            post_content = response.text
        if "comment" in response.url:    #将评论链接作为详情页
            post_content = response.css("#M_").get()    #保存微博内容
            if post_content == None:
                post_content = "无法获取内容"
            for div in response.css(".c").getall():
                if r'id="C_' in div:
                    post_content = post_content + "<span>评论：</span>" + div    #保存评论内容
            post_content = re.sub(r"<a[^>]*>举报</a>","",post_content)    #删去不需要的页面元素
            post_content = re.sub(r"<a[^>]*>收藏</a>","",post_content)
            post_content = re.sub(r"<a[^>]*>操作</a>","",post_content)
            post_content = re.sub(r"<a[^>]*>回复</a>","",post_content)
            post_content = re.sub(r"<a[^>]*>删除</a>","",post_content)
            post_content = re.sub(r"<a[^>]*>关注她</a>","",post_content)
            post_content = re.sub(r"<a[^>]*>关注他</a>","",post_content)
            post_content = re.sub(r"<a[^>]*>原图</a>","",post_content)
            post_content = post_content.replace(r"<!-- 是否进行翻译 -->        &nbsp;    ","<br />")    #在时间前加一行空格
            
        images = []
        srcs = []
        if self.all_HD_pic:
            srcs = response.css("a").getall()
            srcs = [x.split(r'"')[1] for x in srcs if "原图" in x]
        else:
            srcs = response.css("img.ib::attr(src)").getall()    #获取图片url
        for src in srcs:    #清洗图片url，获取图片名
            imagename = src.split('=')[2]
            imagename = imagename.split('&')[0]
            if "." not in imagename:
                imagename = imagename + ".jpg"
            imageurl = "http://wx2.sinaimg.cn/large/" + imagename
            # self.log(f'Replace {src}')
                
            post_content = re.sub(r'"[^"]*'+imagename+r'"',f"./Images/{imagename}",post_content)    #替换图片url
            post_content = re.sub(r'href="/mblog/pic/[^"]*"',"",post_content)
            if len(src) < 200:
                if os.path.exists(f"./Result/Images/{imagename}") == False:    #防止重复下载
                    images.append(imageurl)
                    # self.log(f'Find image {imageurl}')
                # else:
                    # self.log("Image already exists")
            else:
                self.log(f'\n------Too long imageurl in {filename}------\n')
        
        if self.all_HD_pic:
            picall = response.css("a").getall()
            picall = [x.split(r'"')[1] for x in picall if "组图" in x]
            for url in picall:
                picallfilename = url.split('/')[-1].split('?')[0].strip()
                if "." not in picallfilename:
                    picallfilename = picallfilename + ".html"
                if post_content!= None:
                    post_content = re.sub(r"<a[^>]*>组图共.?张</a>",f'<a href=\"{picallfilename}\">组图</a>',post_content)
            if "/mblog/picAll/" in response.url:
                picallfilename = response.url.split('/')[-1].split('?')[0].strip()
                if "." not in picallfilename:
                    picallfilename = picallfilename + ".html"
                with open(f"./Result/{picallfilename}", 'w',encoding='utf-8') as f:
                    f.write(post_content)
                    self.log(f'Saved file {picallfilename}')
        
        if post_content not in self.weibos and title != "":
            self.weibos[post_content] = title    #将post_content作为键，title（发布时间）作为值存入字典
        
        if len(self.weibos) >= self.weibos_in_file:    #达到指定条数的微博时保存成文件
            with open(f"./Result/{filename}", 'w',encoding='utf-8') as f:
                for weibo in sorted(self.weibos.items(),key = lambda x:x[1],reverse = True):    #按发布时间排序
                    if weibo[0] != None:
                        f.write(weibo[0])
                        f.write(self.seperator)
            if os.path.getsize(f"./Result/{filename}") == 0:    #防止重复保存
                os.remove(f"./Result/{filename}")
            else:
                self.log(f'Saved file {filename}')
            self.weibos.clear()
                
        return images
        
    def parse(self, response): 
        images = []
        try:
            images = self.saveFiles(response)
        except TypeError:
            self.log("\n------TypeError------\n")
        if images:
            item = ImageItem()
            item['image_urls'] = images
            yield item    #下载图片
        
        if "comment" not in response.url:
            details = response.css('.c::attr(id)').getall()    #获取详情页链接
            for detail_url in details[::-1]:
                if len(detail_url) != 0:
                    detail_url = "https://weibo.cn/comment/" + detail_url.replace("M_","")
                    yield scrapy.Request(detail_url, cookies=self.cookies)    
        if self.all_HD_pic:
            picall = response.css("a::attr(href)").getall()
            picall = [x for x in picall if r"/mblog/picAll/" in x]
            
            for picurl in picall:
                if len(picurl) != 0:
                    if "https" not in picurl:
                        picurl = "https://weibo.cn/" + picurl
                    yield scrapy.Request(picurl, cookies=self.cookies)    #下载组图页面
                    
    def closed(self,reason):
        weibos_sorted = sorted(self.weibos.items(),key = lambda x:x[1],reverse = True)
        title = weibos_sorted[-1][1]
        filename = re.sub(r'[\/\\\:\*\?\"\<\>\|]','_',f"{title}.html")
        with open(f"./Result/{filename}", 'w',encoding='utf-8') as f:
            for weibo in weibos_sorted:
                if weibo[0] != None:
                    f.write(weibo[0])
                    f.write("<span>————————————————————</span>")            
            self.log(f'Saved file {filename}')
        self.weibos.clear()
        os._exit(0)
        
