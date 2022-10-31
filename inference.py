from Dataset.MaskDataset import MaskDataset
from utils.model_manage import load_checkpoint
import torch
from easydict import EasyDict
from torchvision import transforms
from torch.utils.data import DataLoader
from tqdm import tqdm
import pandas as pd
import os
from Modules.EfficientNet import create_model

if __name__ == "__main__":
    config = EasyDict({
        'image_root_path': "/opt/ml/input/data/eval/images",
        'data_csv_path': '/opt/ml/input/data/eval/info.csv',
        'batch_size': 64,
        'learning_rate': 1e-3,
        'Train_type': ("Train", "Validation", "Test"),
        'model_name': "EfficientNet_b0",
        'seed': 41,
        'image_size': (512, 384),
        'crop_size': (298, 224),
        'desc': 'Normalize_FL_b1',
        'mean': [0.548, 0.504, 0.479],  ## mask: [0.558, 0.512, 0.478], imageNet: [0.485, 0.456, 0.406], baseline: [0.548, 0.504, 0.479]
        'std': [0.237, 0.247, 0.246],   ## mask: [0.218, 0.238, 0.252], imageNet: [0.229, 0.224, 0.225], baseline: [0.237, 0.247, 0.246]
        'checkpoint_path': '/opt/ml/code/runs/2022-10-28-014424-EfficientNet_b0-FL_b0_BN_CCrop'
    })

    transforms = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(config.image_size),
        transforms.CenterCrop(config.crop_size),
        transforms.ToTensor(),
        transforms.Normalize(config.mean, config.std)  
    ])  


    test_dataset = MaskDataset(
        image_root_path = config.image_root_path,
        data_csv_path = config.data_csv_path, 
        split_rate = 0, 
        train_type = config.Train_type[2],
        is_inference = True,
        transform = transforms,
        is_soft_label = False
    )

    test_dataloader = DataLoader(test_dataset, config.batch_size, shuffle=False, num_workers=4, drop_last=False)
    model = create_model(config.model_name)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    model.to(device)
    load_checkpoint(torch.load(f'{config.checkpoint_path}/checkpoint.pth.tar'), model, optimizer)
    submission = pd.read_csv(config.data_csv_path)

    with torch.no_grad():
        model.eval()
        all_predictions = []
        
        for images in tqdm(test_dataloader):
            images = images.to(device)
            predict = model(images)
            predict = predict.argmax(dim=-1)
            all_predictions.extend(predict.detach().cpu().numpy())

    submission['ans'] = all_predictions

    # 제출할 파일을 저장합니다.
    submission.to_csv(os.path.join(config.checkpoint_path, 'submission.csv'), index=False)
    print('test inference is done!')