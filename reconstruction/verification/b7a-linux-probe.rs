//! Standalone B7a fixture. Link against the workspace build; do not edit GPUI.
use gpui::{
    App, AppContext, Bounds, Context, IntoElement, ParentElement, Render, Styled, Window,
    WindowBounds, WindowKind, WindowOptions, px, rgb, size,
};
use std::time::{Duration, Instant};

struct Fixture {
    load: bool,
    report_draw: bool,
}

impl Render for Fixture {
    fn render(&mut self, _: &mut Window, _: &mut Context<Self>) -> impl IntoElement {
        if self.load {
            std::thread::sleep(Duration::from_millis(8));
        }
        if self.report_draw {
            println!("DRAW");
        }
        gpui::div()
            .size_full()
            .bg(rgb(0x284f7d))
            .child(gpui::div().size(px(32.)).bg(rgb(0xeaad27)))
    }
}

fn record_frames(window: &Window, start: Instant, index: u32) {
    window.on_next_frame(move |window, _| {
        println!("FRAME {index} {}", start.elapsed().as_micros());
        if index < 60 {
            window.refresh();
            record_frames(window, start, index + 1);
        }
    });
}

fn main() -> std::process::ExitCode {
    env_logger::init();
    let mode = std::env::args().nth(1).expect("mode");
    if mode == "offscreen" {
        use gpui::PlatformHeadlessRenderer;
        let result = gpui_wgpu::WgpuHeadlessRenderer::new().and_then(|mut renderer| {
            let mut scene = gpui::Scene::default();
            scene.finish();
            renderer.render_scene_to_image(
                &scene,
                gpui::size(gpui::DevicePixels(64), gpui::DevicePixels(64)),
            )
        });
        return match result {
            Ok(image) => {
                println!("OFFSCREEN_OK {}x{}", image.width(), image.height());
                std::process::ExitCode::SUCCESS
            }
            Err(error) => {
                println!("OFFSCREEN_ERR {error:#}");
                std::process::ExitCode::FAILURE
            }
        };
    }
    if mode == "capture" {
        use std::{cell::RefCell, sync::Arc};
        let renderer = match gpui_wgpu::WgpuHeadlessRenderer::new() {
            Ok(renderer) => RefCell::new(Some(renderer)),
            Err(error) => {
                eprintln!("CAPTURE_INIT_ERR {error:#}");
                return std::process::ExitCode::FAILURE;
            }
        };
        let mut app = gpui::HeadlessAppContext::with_platform(
            gpui_platform::current_platform(true).text_system(),
            Arc::new(()),
            move || renderer.take().map(|renderer| Box::new(renderer) as _),
        );
        let window = app
            .open_window(size(px(256.), px(192.)), |_, cx| {
                cx.new(|_| Fixture {
                    load: false,
                    report_draw: false,
                })
            })
            .expect("open capture window");
        let output = std::env::args().nth(2).expect("capture path");
        app.capture_screenshot(window.into())
            .expect("capture scene")
            .save(output)
            .expect("save capture");
        return std::process::ExitCode::SUCCESS;
    }
    assert!(matches!(
        mode.as_str(),
        "open" | "idle" | "cadence" | "loaded" | "capture-live"
    ));
    gpui_platform::application().run(move |cx: &mut App| {
        println!("HOST {}", cx.compositor_name());
        let bounds = Bounds::centered(None, size(px(256.), px(192.)), cx);
        let mut options = WindowOptions::new().window_bounds(Some(WindowBounds::Windowed(bounds)));
        if mode == "capture-live" {
            // The compositor otherwise tiles the fixture and changes its viewport.
            options.kind = WindowKind::PopUp;
        }
        let result = cx.open_window(options, |window, cx| {
            window.set_window_title("GPUI B7a probe");
            cx.new(|_| Fixture {
                load: mode == "loaded",
                report_draw: mode == "idle",
            })
        });
        match result {
            Ok(window) => {
                println!("OPEN_OK");
                window
                    .update(cx, |_, window, _| {
                        println!("SCALE {}", window.scale_factor());
                        if matches!(mode.as_str(), "cadence" | "loaded") {
                            record_frames(window, Instant::now(), 1);
                        }
                    })
                    .expect("update open window");
                let timer = cx.background_executor().timer(Duration::from_secs(4));
                cx.spawn(async move |app| {
                    timer.await;
                    let _ = app.update(|cx| cx.quit());
                })
                .detach();
            }
            Err(error) => {
                println!("OPEN_ERR {error:#}");
                cx.quit();
            }
        }
    });
    std::process::ExitCode::SUCCESS
}
