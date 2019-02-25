# modified from
# https://github.com/pytorch/vision/blob/master/torchvision/datasets/folder.py
# to support folders with two files per sample
# Galen Weld, Feb 2019

import torch.utils.data as data

from PIL import Image

import os
import os.path
import sys


def make_dataset(dir, class_to_idx):
    images = []
    dir = os.path.expanduser(dir)
    for target in sorted(class_to_idx.keys()):
        d = os.path.join(dir, target)
        if not os.path.isdir(d):
            continue

        for root, _, fnames in sorted(os.walk(d)):
            sample_roots = set() # not including extensions here
            for fname in sorted(fnames):
                basename, ext  = os.path.splitext(fname)
                if ext in ('.jpg', '.json'):
                    sample_roots.add(basename)
            for basename in sample_roots:
                    img_path  = os.path.join(root, basename + '.jpg')
                    meta_path = os.path.join(root, basename + '.json')
                    item = (img_path, meta_path, class_to_idx[target])
                    if os.path.exists(img_path) and os.path.exists(meta_path):
                        images.append(item)
                    if not os.path.exists(img_path):
                        print "Couldn't find img {}".format(img_path)
                    if not os.path.exists(meta_path):
                        print "Couldn't find meta {}".format(meta_path)

    return images

def pil_loader(path):
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    with open(path, 'rb') as f:
        img = Image.open(f)
        return img.convert('RGB')


def accimage_loader(path):
    import accimage
    try:
        return accimage.Image(path)
    except IOError:
        # Potentially a decoding problem, fall back to PIL.Image
        return pil_loader(path)


def default_loader(path):
    from torchvision import get_image_backend
    if get_image_backend() == 'accimage':
        return accimage_loader(path)
    else:
        return pil_loader(path)


class TwoFileFolder(data.Dataset):
    """A custom data loader for project sidewalk data where the samples are arranged in this way:
        root/class_x/xxx.jpg
        root/class_x/xxx.json
        root/class_x/xxy.jpg
        root/class_x/xxy.json
        root/class_y/123.ext
    Where each sample has two associated files, an image, and a .json metadata file

    Args:
        root (string): Root directory path.
        loader (callable): A function to load a sample given its path.
        extensions (list[string]): A list of allowed extensions.
        transform (callable, optional): A function/transform that takes in
            a sample and returns a transformed version.
            E.g, ``transforms.RandomCrop`` for images.
        target_transform (callable, optional): A function/transform that takes
            in the target and transforms it.
     Attributes:
        classes (list): List of the class names.
        class_to_idx (dict): Dict with items (class_name, class_index).
        samples (list): List of (sample path, class_index) tuples
        targets (list): The class_index value for each image in the dataset
    """

    def __init__(self, root, transform=None, target_transform=None):
        classes, class_to_idx = self._find_classes(root)
        samples = make_dataset(root, class_to_idx)
        if len(samples) == 0:
            raise(RuntimeError("Found 0 files in subfolders of: " + root + "\n"
                               "Supported extensions are: " + ",".join( ('.jpg', '.json') )))

        self.root = root
        self.loader = default_loader
        self.extensions = ('.jpg', '.json')

        self.classes = classes
        self.class_to_idx = class_to_idx
        self.samples = samples # list of tuples, (img_path, meta_path, target_idx)
        self.targets = [s[2] for s in samples]

        self.transform = transform
        self.target_transform = target_transform

    def _find_classes(self, dir):
        """
        Finds the class folders in a dataset.
        Args:
            dir (string): Root directory path.
        Returns:
            tuple: (classes, class_to_idx) where classes are relative to (dir), and class_to_idx is a dictionary.
        Ensures:
            No class is a subdirectory of another.
        """
        if sys.version_info >= (3, 5):
            # Faster and available in Python 3.5 and above
            classes = [d.name for d in os.scandir(dir) if d.is_dir()]
        else:
            classes = [d for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]
        classes.sort()
        class_to_idx = {classes[i]: i for i in range(len(classes))}
        return classes, class_to_idx

    def __getitem__(self, index):
        """
        Args:
            index (int): Index
        Returns:
            tuple: (sample, target) where target is class_index of the target class.
        """
        img_path, meta_path, target = self.samples[index]
        img = self.loader(img_path)
        if self.transform is not None:
            img = self.transform(img)
        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target

    def __len__(self):
        return len(self.samples)

    def __repr__(self):
        fmt_str = 'Dataset ' + self.__class__.__name__ + '\n'
        fmt_str += '    Number of datapoints: {}\n'.format(self.__len__())
        fmt_str += '    Root Location: {}\n'.format(self.root)
        tmp = '    Transforms (if any): '
        fmt_str += '{0}{1}\n'.format(tmp, self.transform.__repr__().replace('\n', '\n' + ' ' * len(tmp)))
        tmp = '    Target Transforms (if any): '
        fmt_str += '{0}{1}'.format(tmp, self.target_transform.__repr__().replace('\n', '\n' + ' ' * len(tmp)))
        return fmt_str