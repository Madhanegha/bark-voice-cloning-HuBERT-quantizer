import os.path

import numpy
import torch
from torch import nn, optim


class CustomTokenizer(nn.Module):
    def __init__(self, hidden_size=1024, input_size=768, output_size=10000):
        super(CustomTokenizer, self).__init__()

        self.l1 = nn.Linear(input_size, hidden_size)
        self.l2 = nn.Linear(hidden_size, output_size)
        self.sm = nn.Softmax(dim=1)
        self.optimizer: optim.Optimizer = None
        self.lossfunc = nn.CrossEntropyLoss()
        self.output_size = output_size

    def forward(self, x):
        x = self.l1(x)
        x = self.l2(x)
        x = self.sm(x)
        return x

    @torch.no_grad()
    def get_token(self, x):
        """
        Used to get the token for the first
        :param x: An array with shape (N, input_size) where N is a whole number greater or equal to 1, and input_size is the input size used when creating the model.
        :return: An array with shape (N,) where N is the same as N from the input. Every number in the array is a whole number in range 0...output_size - 1 where output_size is the output size used when creating the model.
        """
        return torch.argmax(self(x), dim=1)

    def prepare_training(self):
        self.optimizer = optim.Adam(self.parameters(), 0.001)

    def train_step(self, x_train, y_train, log_loss=False):
        y_train = y_train[:-1]
        y_train_hot = torch.zeros(len(y_train), self.output_size)
        y_train_hot[range(len(y_train)), y_train] = 1
        y_train_hot = y_train_hot.to('cuda')

        optimizer = self.optimizer
        lossfunc = self.lossfunc
        # Zero the gradients
        self.zero_grad()

        # Forward pass
        y_pred = self(x_train)

        # Calculate the loss
        loss = lossfunc(y_pred, y_train_hot)

        # Print loss
        if log_loss:
            print('Loss', loss.item())

        # Backward pass
        loss.backward()

        # Update the weights
        optimizer.step()


def auto_train(data_path, save_path='model.pth', load_model: str | None = None, save_epochs=5):
    data_x, data_y = [], []

    model_training = CustomTokenizer().to('cuda')
    save_path = os.path.join(data_path, save_path)
    if load_model and os.path.isfile(load_model):
        print('Loading model from', load_model)
        model_training.load_state_dict(torch.load(load_model))
    else:
        print('Creating new model.')

    sem_string = '_semantic.npy'
    feat_string = '_semantic_features.npy'

    ready = os.path.join(data_path, 'ready')
    for input_file in os.listdir(ready):
        full_path = os.path.join(ready, input_file)
        if input_file.endswith(sem_string):
            data_y.append(numpy.load(full_path))
        elif input_file.endswith(feat_string):
            data_x.append(numpy.load(full_path))
    model_training.prepare_training()

    epoch = 1

    while 1:
        for i in range(save_epochs):
            j = 0
            for x, y in zip(data_x, data_y):
                model_training.train_step(torch.tensor(x).to('cuda'), torch.tensor(y).to('cuda'), j % 50 == 0)  # Print loss every 50 steps
                j += 1
        torch.save(model_training.state_dict(), save_path)
        print(f'Epoch {epoch} completed')
        epoch += 1
