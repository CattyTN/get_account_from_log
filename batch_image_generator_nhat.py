from BingImageCreator import ImageGenAsync
import asyncio
import os
import logging
from datetime import datetime
from typing import List, Dict
from tqdm import tqdm
import aiohttp
import aiofiles
import time
import shutil
import json

class BatchImageGenerator:
    def __init__(
        self,
        auth_cookie: str,
        output_base_dir: str = "batch_generated_images",
        debug_file: str = "batch_generation.log",
        rate_limit_delay: int = 3,
        max_retries: int = 3,
        timeout: int = 30
    ):
        # Khởi tạo logging
        self.setup_logging(debug_file)
        
        # Validate cookie
        if not auth_cookie or len(auth_cookie) < 10:
            raise ValueError("Cookie không hợp lệ hoặc thiếu giá trị _U")
        
        # Khởi tạo các thuộc tính
        self.auth_cookie = auth_cookie
        self.output_base_dir = output_base_dir
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Xóa và tạo lại thư mục output
        if os.path.exists(output_base_dir):
            shutil.rmtree(output_base_dir)
        
        # Tạo cấu trúc thư mục
        os.makedirs(output_base_dir)
        os.makedirs(os.path.join(output_base_dir, "logs"))
        
        # Định nghĩa paths
        self.logs_dir = os.path.join(output_base_dir, "logs")
        self.status_file = os.path.join(self.logs_dir, "generation_status.txt")
        self.prompt_log = os.path.join(self.logs_dir, "prompt_log.txt") 
        self.error_log = os.path.join(self.logs_dir, "error_log.txt")
        self.stats_file = os.path.join(self.logs_dir, "statistics.json")
        
        # Khởi tạo image generator
        self.image_generator = ImageGenAsync(auth_cookie)
        
        # Khởi tạo statistics
        self.stats = {
            "total_prompts": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
            "duration": None
        }

    def setup_logging(self, debug_file: str) -> None:
        """Thiết lập logging"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(debug_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def load_prompts(self, input_file: str) -> List[Dict]:
        """Get prompts """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Không tìm thấy file {input_file}")
            
        prompts = []
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Lọc dòng trống và khoảng trắng
            lines = [line.strip() for line in lines if line.strip()]
            
            self.logger.info(f"Đọc được {len(lines)} prompts từ file")
            self.logger.debug(f"Nội dung prompts: {lines}")
            
            # Tạo dictionary cho mỗi prompt
            for i, prompt in enumerate(lines, 1):
                prompts.append({
                    'id': i,
                    'prompt': prompt,
                    'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
                })
            
            self.stats["total_prompts"] = len(prompts)
            return prompts
            
        except Exception as e:
            self.logger.error(f"Lỗi đọc prompts: {str(e)}")
            raise

    async def save_images(self, image_urls: List[str], output_dir: str) -> bool:
        """Lưu ảnh từ URLs"""
        try:
            if not image_urls:
                return False
                
            os.makedirs(output_dir, exist_ok=True)
            
            async with aiohttp.ClientSession() as session:
                for i, url in enumerate(image_urls, 1):
                    try:
                        async with session.get(url, timeout=self.timeout) as response:
                            if response.status == 200:
                                # Đọc nội dung ảnh
                                content = await response.read()
                                # Kiểm tra kích thước ảnh (20 KB = 20480 bytes)
                                if len(content) > 20480:
                                    file_path = os.path.join(output_dir, f"image_{i}.jpg")
                                    async with aiofiles.open(file_path, 'wb') as f:
                                        await f.write(content)
                                else:
                                    self.logger.warning(f"Ảnh tại {url} nhỏ hơn 20 KB, bỏ qua.")
                            else:
                                self.logger.error(f"Lỗi HTTP {response.status} khi tải {url}")
                                return False
                    except Exception as e:
                        self.logger.error(f"Lỗi khi tải ảnh {url}: {str(e)}")
                        return False
                        
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu ảnh: {str(e)}")
            return False

    def log_error(self, prompt_id: int, prompt: str, error: str) -> None:
        """Log lỗi ra file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.error_log, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} | ID: {prompt_id} | Prompt: {prompt} | Error: {error}\n")
        except Exception as e:
            self.logger.error(f"Lỗi khi ghi error log: {str(e)}")

    def save_statistics(self) -> None:
        """Lưu thống kê"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu thống kê: {str(e)}")

    async def generate_single(self, prompt_data: Dict) -> None:
        """Xử lý một prompt đơn lẻ"""
        prompt_id = prompt_data['id']
        prompt = prompt_data['prompt']
        timestamp = prompt_data['timestamp']
        
        try:
            # Tạo thư mục output cho prompt này
            output_dir = os.path.join(
                self.output_base_dir,
                f"prompt_{prompt_id}_{timestamp}"
            )
            
            # Gọi API để tạo ảnh
            image_urls = await self.image_generator.get_images(prompt)
            
            if not image_urls:
                raise Exception("Không nhận được URLs ảnh")
                
            self.logger.debug(f"Nhận được URLs: {image_urls}")
            
            # Lưu ảnh
            if await self.save_images(image_urls, output_dir):
                self.stats["successful"] += 1
                status = "success"
            else:
                self.stats["failed"] += 1
                status = "failed"
                
            # Log kết quả
            with open(self.prompt_log, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} | ID: {prompt_id} | Status: {status} | Prompt: {prompt}\n")
                
        except Exception as e:
            self.stats["failed"] += 1
            error_msg = str(e)
            self.logger.error(f"Lỗi xử lý prompt {prompt_id}: {error_msg}")
            self.log_error(prompt_id, prompt, error_msg)

    async def generate_batch(self, input_file: str) -> None:
        """Xử lý batch prompts từ file"""
        try:
            # Bắt đầu đếm thời gian
            self.stats["start_time"] = datetime.now().isoformat()
            
            # Đọc prompts
            prompts = self.load_prompts(input_file)
            
            if not prompts:
                self.logger.info("Không có prompt nào để xử lý")
                return
                
            # Xử lý từng prompt với thanh tiến trình
            with tqdm(total=len(prompts), desc="Đang xử lý") as pbar:
                for prompt_data in prompts:
                    try:
                        await self.generate_single(prompt_data)
                    except Exception as e:
                        self.logger.error(f"Lỗi không mong đợi: {str(e)}")
                    finally:
                        await asyncio.sleep(self.rate_limit_delay)
                        pbar.update(1)
            
            # Kết thúc và lưu thống kê
            self.stats["end_time"] = datetime.now().isoformat()
            duration = datetime.fromisoformat(self.stats["end_time"]) - \
                      datetime.fromisoformat(self.stats["start_time"])
            self.stats["duration"] = str(duration)
            
            self.save_statistics()
            self.logger.info(f"Hoàn thành xử lý batch trong {duration}")
            
        except Exception as e:
            self.logger.error(f"Lỗi trong quá trình xử lý batch: {str(e)}")
            raise

async def main():
    # Cookie _U từ Bing
    cookie_value = ""
    try:
        generator = BatchImageGenerator(
            auth_cookie=cookie_value,
            output_base_dir="batch_generated_images",
            rate_limit_delay=3,
            max_retries=3,
            timeout=30
        )
        
        await generator.generate_batch("prompts.txt")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        logging.error(f"Lỗi chính: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())