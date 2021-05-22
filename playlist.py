import json


class Playlist:
    def __init__(self):
        self.playlist_content = []

    def add(self, new_item):
        self.playlist_content.append(new_item)
    
    def remove(self, item):
        if item not in self.playlist_content:
            raise Exception("<!!> Item to remove not founod in playlist.")
        self.playlist_content.remove(item)
    
    def remove_idx(self, item_idx):
        if item_idx >= len(self.playlist_content) or item_idx < 0:
            raise IndexError(f"<!!> Item index to remove {item_idx} out of bounds")
        self.playlist_content.pop(item_idx)
    
    @staticmethod
    def load_from_file(filepath):
        fp = open(filepath, "r")
        playlist_content = json.load(fp)
        fp.close()
        
        new_playlist = Playlist()

        for playlist_item in playlist_content:
            new_playlist_item = PlaylistItem.create_from_list(playlist_item)
            new_playlist.add(new_playlist_item)
        
        return new_playlist


class PlaylistItem:
    def __init__(self):
        self.media_list = []

    def add_media(self, media_url):
        if not self.validate_media(media_url):
            raise Exception(f"<!!> Invalid media url : {media_url}")
        self.media_list.append(media_url)
    
    def validate_media(self, media_url):
        return True

    @staticmethod
    def create_from_list(media_list):
        if type(media_list) is not list:
            raise TypeError(f"<!!> media_list should be a list. (it's {type(media_list)})")
        
        new_item = PlaylistItem()
        for m in media_list:
            new_item.add_media(m)

        return new_item
    

if __name__ == "__main__":
    p = Playlist.load_from_file("playlist_test.json")
    print(p.playlist_content)
    print(p.playlist_content[0].media_list)