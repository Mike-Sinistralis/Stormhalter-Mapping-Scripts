from PIL import Image

DEBUG = False

bitmaps = {}
sprites = {}


def extract_sprite(texture, cx, cy, sx, sy, ox, oy, color):
    global bitmaps, sprites
    if DEBUG:
        import os
        debug_count = 0
        print(
            f"{debug_count:0>3} texture:{texture}, cx:{cx}, cy:{cy}"
            f" sx:{sx}, sy:{sy}, ox:{ox}, oy:{oy}, color:{color}")

    if texture not in bitmaps:
        bitmaps[texture] = Image.open(rf".\unxnb\{texture}.png")

    # multi level dictionary
    d = sprites
    n = 0
    for k in (texture, cx, cy):
        n += 1
        try:
            d = d[k]
        except KeyError:
            if n < 3:
                d[k] = {}
                d = d[k]
            else:
                d[k] = bitmaps[texture].crop((cx, cy, cx + sx, cy + sy))
    sprite = sprites[texture][cx][cy]

    if DEBUG:
        fn = rf".\debug\{debug_count:0>3}-s1.png"
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        sprite.save(fn)

    if color != "-":
        cr, cg, cb, ca = map(int, color.strip("()").split(","))

        if DEBUG:
            print(f"{debug_count:0>3} cr:{cr}, cg:{cg}, cb:{cb}, ca:{ca}")

        source = sprite.split()
        nr = source[0].point(lambda i: i * cr / 255)
        ng = source[1].point(lambda i: i * cg / 255)
        nb = source[2].point(lambda i: i * cb / 255)
        na = source[3].point(lambda i: i * ca / 255)
        sprite = Image.merge(sprite.mode, (nr, ng, nb, na))

        if DEBUG:
            fn = rf".\debug\{debug_count:0>3}-s2.png"
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            sprite.save(fn)

    if (ox != 0
    or oy != 0):
        if (sx < 200
        or sy < 200):
            oxp = ox  # as pixels
            oyp = oy
        else:
            oxp = int(ox * sx / 100)  # as percentages
            oyp = int(oy * sy / 100)
        nx = sx + abs(oxp)
        if oxp < 0:
            px = 0
            cx = -oxp
        else:
            px = oxp
            cx = 0
        ny = sy + abs(oyp)
        if oyp < 0:
            py = 0
            cy = -oyp
        else:
            py = oyp
            cy = 0

        if DEBUG:
            print(
                f"{debug_count:0>3} offset nx:{nx}, ny:{ny}"
                f" px:{px}, py:{py}, cx:{cx}, cy:{cy}")

        adjust = Image.new(
            mode="RGBA",
            size=(nx, ny),
            color=(0, 0, 0, 0))
        adjust.paste(sprite, (px, py))

        if DEBUG:
            fn = rf".\debug\{debug_count:0>3}-s3.png"
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            adjust.save(fn)

        if (cx != 0
        or cy != 0):
            adjust = adjust.crop((cx, cy, sx + cx, sy + cy))

            if DEBUG:
                fn = rf".\debug\{debug_count:0>3}-s4.png"
                os.makedirs(os.path.dirname(fn), exist_ok=True)
                adjust.save(fn)

        sprite = adjust

    if sprite.size != (200, 200):

        if DEBUG:
            print(f"{debug_count:0>3} resized from:{sprite.size}")

        sprite = sprite.resize((200, 200), resample=Image.LANCZOS)

        if DEBUG:
            fn = rf".\debug\{debug_count:0>3}-s5.png"
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            sprite.save(fn)

    return sprite
