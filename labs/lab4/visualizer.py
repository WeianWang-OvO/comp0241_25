"""
Visualization library for COLMAP sparse reconstruction outputs.
"""
import random
import time
from pathlib import Path
from typing import List

import imageio.v3 as iio
import numpy as np
import viser
import viser.transforms as tf
from viser.extras.colmap import (
    read_cameras_binary,
    read_images_binary,
    read_points3d_binary,
)
from tqdm.auto import tqdm


class ColmapVisualizer:
    def __init__(
        self,
        colmap_path: Path,
        images_path: Path,
        downsample_factor: int = 2,
    ):
        """Initialize the COLMAP visualizer.

        Args:
            colmap_path: Path to the COLMAP reconstruction directory.
            images_path: Path to the COLMAP images directory.
            downsample_factor: Downsample factor for the images.
        """
        self.colmap_path = colmap_path
        self.images_path = images_path
        self.downsample_factor = downsample_factor
        self.server = viser.ViserServer()
        self.server.gui.configure_theme(titlebar_content=None, control_layout="collapsible")
        
        # Load COLMAP data
        self.cameras = read_cameras_binary(colmap_path / "cameras.bin")
        self.images = read_images_binary(colmap_path / "images.bin")
        self.points3d = read_points3d_binary(colmap_path / "points3D.bin")
        
        # Initialize GUI elements
        self._setup_gui()
        
        # Initialize visualization elements
        self.points = np.array([self.points3d[p_id].xyz for p_id in self.points3d])
        self.colors = np.array([self.points3d[p_id].rgb for p_id in self.points3d])
        self.frames: List[viser.FrameHandle] = []
        self.need_update = True
        
        # Initialize point cloud
        point_mask = np.random.choice(self.points.shape[0], self.gui_points.value, replace=False)
        self.point_cloud = self.server.scene.add_point_cloud(
            name="/colmap/pcd",
            points=self.points[point_mask],
            colors=self.colors[point_mask],
            point_size=self.gui_point_size.value,
        )

    def _setup_gui(self):
        """Set up GUI controls."""
        self.gui_reset_up = self.server.gui.add_button(
            "Reset up direction",
            hint="Set the camera control 'up' direction to the current camera's 'up'.",
        )
        
        @self.gui_reset_up.on_click
        def _(event: viser.GuiEvent) -> None:
            client = event.client
            assert client is not None
            client.camera.up_direction = tf.SO3(client.camera.wxyz) @ np.array([0.0, -1.0, 0.0])

        self.gui_points = self.server.gui.add_slider(
            "Max points",
            min=1,
            max=len(self.points3d),
            step=1,
            initial_value=min(len(self.points3d), 50_000),
        )
        
        self.gui_frames = self.server.gui.add_slider(
            "Max frames",
            min=1,
            max=len(self.images),
            step=1,
            initial_value=min(len(self.images), 100),
        )
        
        self.gui_point_size = self.server.gui.add_slider(
            "Point size",
            min=0.01,
            max=0.1,
            step=0.001,
            initial_value=0.05,
        )
        
        # Set up GUI callbacks
        @self.gui_points.on_update
        def _(_) -> None:
            point_mask = np.random.choice(self.points.shape[0], self.gui_points.value, replace=False)
            self.point_cloud.points = self.points[point_mask]
            self.point_cloud.colors = self.colors[point_mask]

        @self.gui_frames.on_update
        def _(_) -> None:
            self.need_update = True

        @self.gui_point_size.on_update
        def _(_) -> None:
            self.point_cloud.point_size = self.gui_point_size.value

    def visualize_frames(self):
        """Send all COLMAP elements to viser for visualization."""
        # Remove existing image frames
        for frame in self.frames:
            frame.remove()
        self.frames.clear()

        # Interpret the images and cameras
        img_ids = [im.id for im in self.images.values()]
        random.shuffle(img_ids)
        img_ids = sorted(img_ids[: self.gui_frames.value])

        def attach_callback(
            frustum: viser.CameraFrustumHandle, frame: viser.FrameHandle
        ) -> None:
            @frustum.on_click
            def _(_) -> None:
                for client in self.server.get_clients().values():
                    client.camera.wxyz = frame.wxyz
                    client.camera.position = frame.position

        for img_id in tqdm(img_ids):
            img = self.images[img_id]
            cam = self.cameras[img.camera_id]

            # Skip images that don't exist
            image_filename = self.images_path / img.name
            if not image_filename.exists():
                continue

            T_world_camera = tf.SE3.from_rotation_and_translation(
                tf.SO3(img.qvec), img.tvec
            ).inverse()
            frame = self.server.scene.add_frame(
                f"/colmap/frame_{img_id}",
                wxyz=T_world_camera.rotation().wxyz,
                position=T_world_camera.translation(),
                axes_length=0.1,
                axes_radius=0.005,
            )
            self.frames.append(frame)

            if cam.model != "PINHOLE":
                print(f"Expected pinhole camera, but got {cam.model}")

            H, W = cam.height, cam.width
            fy = cam.params[1]
            image = iio.imread(image_filename)
            image = image[::self.downsample_factor, ::self.downsample_factor]
            frustum = self.server.scene.add_camera_frustum(
                f"/colmap/frame_{img_id}/frustum",
                fov=2 * np.arctan2(H / 2, fy),
                aspect=W / H,
                scale=0.15,
                image=image,
            )
            attach_callback(frustum, frame)

    def run(self):
        """Run the visualization server."""
        while True:
            if self.need_update:
                self.need_update = False
                self.visualize_frames()
            time.sleep(1e-3)


def visualize_reconstruction(colmap_path: Path, images_path: Path, downsample_factor: int = 2):
    """Launch the visualization server for a COLMAP reconstruction.
    
    Args:
        colmap_path: Path to the COLMAP reconstruction directory.
        images_path: Path to the COLMAP images directory.
        downsample_factor: Downsample factor for the images.
    """
    visualizer = ColmapVisualizer(colmap_path, images_path, downsample_factor)
    visualizer.run()


if __name__ == "__main__":
    # Example usage
    import tyro
    tyro.cli(visualize_reconstruction)