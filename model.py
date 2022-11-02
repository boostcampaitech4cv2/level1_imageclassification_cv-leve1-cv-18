import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import efficientnet_b1, efficientnet_b4, efficientnet_v2_l
import torchvision.models as models
from facenet_pytorch import InceptionResnetV1
from efficientnet_pytorch import EfficientNet


class BaseModel(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        self.conv1 = nn.Conv2d(3, 32, kernel_size=7, stride=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.25)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.conv1(x)
        x = F.relu(x)

        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)

        x = self.conv3(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout2(x)

        x = self.avgpool(x)
        x = x.view(-1, 128)
        return self.fc(x)


# Custom Model Template
class MyModel(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.backbone = efficientnet_b1(pretrained=True)
        self.n_features = self.backbone.classifier[1].out_features
        self.classifier = nn.Linear(self.n_features, num_classes)

    def forward(self, x):
        x = self.backbone(x)
        x = self.classifier(x)
        return x


class EfficientNet_B1(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        self.model = models.efficientnet_b1(weights=models.EfficientNet_B1_Weights.DEFAULT)
        self.model.classifier = nn.Sequential(
            nn.Dropout(p=0.8, inplace=True), nn.Linear(1280, num_classes, bias=True)
        )

        self.name = "EfficientNet_B1"

        self.init_params()

    def forward(self, x):
        x = self.model(x)
        return x

    def init_params(self):
        nn.init.kaiming_uniform_(self.model.classifier[1].weight)
        nn.init.zeros_(self.model.classifier[1].bias)


class InceptionResnet(nn.Module):
    """
    Total params: 27,979,383
    Trainable params: 27,979,383
    Non-trainable params: 0
    ----------------------------------------------------------------
    Input size (MB): 2.25
    Forward/backward pass size (MB): 840.53
    Params size (MB): 106.73
    Estimated Total Size (MB): 949.52
    """

    def __init__(self, num_classes):
        super().__init__()
        self.backbone = InceptionResnetV1(pretrained="vggface2", classify=True,)
        self.n_features = self.backbone.logits.out_features
        self.classifier = nn.Linear(self.n_features, num_classes)

        self.init_weights(self.classifier)

    def forward(self, x):
        x = self.backbone(x)
        x = self.classifier(x)
        return x

    def init_weights(self, m):
        nn.init.kaiming_uniform_(m.weight)
        nn.init.constant_(m.bias, 0)


class Efficientnet_v2_l(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.backbone = efficientnet_v2_l(weight="DEFAULT")
        self.n_features = self.backbone.classifier[1].out_features
        self.classifier = nn.Linear(self.n_features, num_classes)

        self.init_weights(self.classifier)

    def forward(self, x):
        x = self.backbone(x)
        x = self.classifier(x)
        return x

    def init_weights(self, m):
        nn.init.kaiming_uniform_(m.weight)
        nn.init.constant_(m.bias, 0)


class InceptionResnet_MS(nn.Module):
    """
    Total params: 27,979,383
    Trainable params: 27,979,383
    Non-trainable params: 0
    ----------------------------------------------------------------
    Input size (MB): 2.25
    Forward/backward pass size (MB): 840.53
    Params size (MB): 106.73
    Estimated Total Size (MB): 949.52
    """

    def __init__(self, num_classes, classifier_num, dropout_p):
        super().__init__()
        self.backbone = InceptionResnetV1(pretrained="vggface2", classify=False)

        self.last_linear = nn.Linear(1792, 512, bias=True)
        self.last_bn = nn.BatchNorm1d(512, eps=0.001, momentum=0.1, affine=True)
        self.logits = nn.Linear(512, num_classes, bias=True)

        self.classifier_num = classifier_num
        self.dropout_p = dropout_p
        self.high_dropout = nn.Dropout(p=self.dropout_p)

        self.init_weights(self.logits)
        self.init_weights(self.last_linear)
        self.init_weights(self.last_bn)

    def forward(self, x):
        x = self.backbone.conv2d_1a(x)
        x = self.backbone.conv2d_2a(x)
        x = self.backbone.conv2d_2b(x)
        x = self.backbone.maxpool_3a(x)
        x = self.backbone.conv2d_3b(x)
        x = self.backbone.conv2d_4a(x)
        x = self.backbone.conv2d_4b(x)
        x = self.backbone.repeat_1(x)
        x = self.backbone.mixed_6a(x)
        x = self.backbone.repeat_2(x)
        x = self.backbone.mixed_7a(x)
        x = self.backbone.repeat_3(x)
        x = self.backbone.block8(x)
        x = self.backbone.avgpool_1a(x)
        x = x.view(x.shape[0], -1)
        x = self.last_linear(x)
        x = self.last_bn(x)
        logits = torch.mean(
            torch.stack(
                [self.logits(self.high_dropout(x)) for _ in range(self.classifier_num)], dim=0,
            ),
            dim=0,
        )
        # x = logits
        return logits

    def init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.kaiming_uniform_(m.weight)
            nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.BatchNorm1d):
            nn.init.constant_(m.weight.data, 1)
            nn.init.constant_(m.bias.data, 0)


class EfficientNetMaster(nn.Module):
    def __init__(self, num_classes: int = 8):
        """
        Anti-SJ model presented by your master
        Total params: 67,075,288
        Trainable params: 67,075,288
        Non-trainable params: 0
        ----------------------------------------------------------------
        Input size (MB): 0.57
        Forward/backward pass size (MB): 1269.24
        Params size (MB): 255.87
        Estimated Total Size (MB): 1525.69
        ----------------------------------------------------------------
        """
        super().__init__()
        self.num_classes = num_classes
        self.model = self.get_efficientnet_model()
        self.model._fc = nn.Sequential(
            nn.Linear(2560, 1280), nn.GELU(), nn.Dropout(0.2), nn.Linear(1280, self.num_classes)
        )
        self.init_weights(self.model._fc)

    def forward(self, x):
        x = self.model(x)
        return x

    def init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.kaiming_uniform_(m.weight)
            nn.init.constant_(m.bias, 0)

    def get_efficientnet_model(self):
        model = EfficientNet.from_pretrained("efficientnet-b7")
        model._fc = nn.Linear(2560, 128)  # match with the original efficientnet-b7
        model.load_state_dict(
            torch.load("/home/ubuntu/yj_study/baseline_v2/modelparam20.pt")
        )  # load model from checkpoint

        # delete the classifier and replace with a new one
        del model._fc
        return model
