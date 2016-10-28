import sys
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5 import QtWidgets, QtGui, QtCore
from sqlite3 import connect


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):

        super(MainWindow, self).__init__()

        self.widget = GlWidget()

        self.setCentralWidget(self.widget)

        self.init_width = 800
        self.ratio = 1024/1344

        self.setGeometry(100, 100, self.init_width, self.init_width*self.ratio)

    def keyPressEvent(self, event):

        self.widget.handle_key_press(event.key())

    def keyReleaseEvent(self, event):

        self.widget.handle_key_release(event.key())

    def mousePressEvent(self, event):

        self.widget.handle_mouse_click(event.pos())


class GlWidget(QtWidgets.QOpenGLWidget):

    color = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "white": (255, 255, 255),
        "black": (0, 0, 0)
    }

    def __init__(self):

        QtWidgets.QOpenGLWidget.__init__(self)

        # ---- FOR THE POINTS ----- #

        self.points_to_draw = []
        self.points_width = 10

        self.textures = {}
        self.textures_folder = "textures"
        self.current_texture = "BC_163_P1L3C1_X5_Color_A568"

        self.pict_rotation_angle = 0
        self.rotation_speed = 0.10

        self.shift_modifier = False
        self.control_modifier = False

    def paintGL(self):

        glPushMatrix()
        glRotated(self.pict_rotation_angle, 0, 0, 1)
        self.draw_textured_rectangle(self.width()/2, self.height()/2, width=self.width(), height=self.height())
        glPopMatrix()

        for x, y in self.points_to_draw:

            self.draw_square(color="red", x=x, y=y, width=self.points_width)

        glFlush()

    def initializeGL(self):

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.width(), self.height(), 0)

        self.load_textures()

        glClearColor(0.0, 0.0, 0.0, 1.0)

    def draw_square(self, x, y, width, color):

        glBegin(GL_QUADS)
        glColor3ub(*self.color[color])
        glVertex2d(x - width/2, y - width/2)
        glVertex2d(x - width/2, y + width/2)
        glVertex2d(x + width/2, y + width/2)
        glVertex2d(x + width/2, y - width/2)
        glEnd()

        glColor3ub(*self.color["white"])

    def draw_textured_rectangle(self, x, y, width, height):

        glEnable(GL_TEXTURE_2D)

        self.textures[self.current_texture].bind()
        glBegin(GL_QUADS)

        glTexCoord2d(0, 1)
        glVertex2d(x - width / 2, y - height / 2)

        glTexCoord2d(0, 0)
        glVertex2d(x - width / 2, y + height / 2)

        glTexCoord2d(1, 0)
        glVertex2d(x + width / 2, y + height / 2)

        glTexCoord2d(1, 1)
        glVertex2d(x + width/2, y - height / 2)

        glEnd()
        glDisable(GL_TEXTURE_2D)

    def load_textures(self):

        self.textures["BC_163_P1L3C1_X5_Color_A568"] = \
            QtGui.QOpenGLTexture(QtGui.QImage("{}/BC_163_P1L3C1_X5_Color_A568".format(self.textures_folder)).mirrored())

    def suppress_point(self, position):

        points_to_suppress = []
        for x, y in self.points_to_draw:

            if (x - self.points_width) < position.x() < (x + self.points_width) and \
                    (y - self.points_width) < position.y() < (y + self.points_width):

                points_to_suppress.append([x, y])

        for coord in points_to_suppress:

            self.points_to_draw.remove(coord)

        self.repaint()

    def save(self):

        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, "", "{}_with_tagged_neurons.tiff".format(self.current_texture), "")

        pixmap = QtGui.QPixmap(self.size())
        self.render(pixmap)
        pixmap.save("{}".format(filename[0]))

    def rotate_image(self, side):

        if side == "left":
            self.pict_rotation_angle -= self.rotation_speed
        else:
            self.pict_rotation_angle += self.rotation_speed
        self.pict_rotation_angle %= 360
        self.repaint()

    def add_point(self, position):

        self.points_to_draw.append([position.x(), position.y()])

        connection = connect("data.db")
        cursor = connection.cursor()

        query = "SELECT `AP`, `DV` FROM neurons WHERE `tagged`=1 AND `slice`='{}'".format(self.current_texture)
        cursor.execute(query)

        ref_st_x, ref_st_y = cursor.fetchone()  # stereotaxic coordinates
        ref_p_x, ref_p_y = position.x(), position.y()  # pixel coordinates

        query = "SELECT `AP`, `DV` FROM neurons WHERE `tagged`=0 AND `slice`='{}'".format(self.current_texture)
        cursor.execute(query)

        st_coordinates = cursor.fetchall()

        query = "SELECT `pixel_size`, `optical_magnification`, `zoom_magnification` FROM slices WHERE `slice`='{}'"\
            .format(self.current_texture)

        try:
            cursor.execute(query)
        except Exception as e:
            print(query)
            raise e
        micro_pixel, magnification, zoom = cursor.fetchone()

        cam_ratio = 1 / ((micro_pixel / 1000) / (zoom * magnification))
        display_ratio = self.width() / self.textures[self.current_texture].width()

        print("cam ratio", cam_ratio)
        print("display ratio", display_ratio)

        print(st_coordinates)

        for st_x, st_y in st_coordinates:

            p_x = ref_p_x + (-1) * (st_x - ref_st_x) * cam_ratio * display_ratio
            p_y = ref_p_y + (st_y - ref_st_y) * cam_ratio * display_ratio
            self.points_to_draw.append([p_x, p_y])

        self.repaint()

    def remove_all_points(self):

        self.points_to_draw = []
        self.repaint()

    def handle_mouse_click(self, position):

        if not self.shift_modifier:
            if len(self.points_to_draw) == 0:
                self.add_point(position)
        else:
            self.suppress_point(position)

    def handle_key_press(self, key):

        if key == QtCore.Qt.Key_Left:

            self.rotate_image("left")

        elif key == QtCore.Qt.Key_Right:

            self.rotate_image("right")

        elif key == QtCore.Qt.Key_Space:

            self.remove_all_points()

        elif key == QtCore.Qt.Key_Shift:

            self.shift_modifier = True

        elif key == QtCore.Qt.Key_Control:

            self.control_modifier = True

        elif key == QtCore.Qt.Key_S and self.control_modifier:

            self.save()

    def handle_key_release(self, key):

        if key == QtCore.Qt.Key_Shift:

            self.shift_modifier = False

        elif key == QtCore.Qt.Key_Control:

            self.control_modifier = False


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
