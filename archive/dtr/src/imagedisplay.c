/*
 * imagedisplay.c
 *
 * Show raw and processed images
 *
 * (c) 2007-2009 Thomas White <taw27@cam.ac.uk>
 *
 *  dtr - Diffraction Tomography Reconstruction
 *
 */

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <gtk/gtk.h>
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>

#include "imagedisplay.h"
#include "utils.h"
#include "mapping.h"

/* Free pixbuf data when reference count drops to zero */
static void imagedisplay_free_data(guchar *image_eightbit,
				   ImageDisplay *imagedisplay)
{
	free(image_eightbit);
}

static void imagedisplay_rescale(ImageDisplay *imagedisplay, unsigned int v_w,
				 unsigned int v_h)
{
	unsigned int w, h;
	float aspect_image, aspect_window;

	w = imagedisplay->imagerecord.width;
	h = imagedisplay->imagerecord.height;

	/* Preserve aspect ratio */
	aspect_image = (float)w/h;
	aspect_window = (float)v_w/v_h;
	if ( aspect_window > aspect_image ) {
		v_w = aspect_image*v_h;
	} else {
		v_h = v_w/aspect_image;
	}

	if ( imagedisplay->pixbuf_scaled ) {
		g_object_unref(imagedisplay->pixbuf_scaled);
	}

	/* Create the scaled pixbuf from the 8-bit display data */
	imagedisplay->pixbuf_scaled = gdk_pixbuf_scale_simple(
						imagedisplay->pixbuf, v_w, v_h,
						GDK_INTERP_BILINEAR);
	imagedisplay->view_width = v_w;
	imagedisplay->view_height = v_h;
}

static gboolean imagedisplay_configure_event(GtkWidget *widget,
					     GdkEventConfigure *event,
					     ImageDisplay *imagedisplay)
{
	imagedisplay->drawingarea_width = event->width;
	imagedisplay->drawingarea_height = event->height;
	imagedisplay_rescale(imagedisplay, event->width, event->height);

	return FALSE;
}

void imagedisplay_put_data(ImageDisplay *imagedisplay, ImageRecord imagerecord)
{
	unsigned int x, y;
	unsigned int w, h;
	int min, max;
	double c, scale;
	int b;

	h = imagerecord.height;
	w = imagerecord.width;

	if ( imagedisplay->pixbuf ) {
		g_object_unref(imagedisplay->pixbuf);
	}

	min = 2<<15;  max = 0;
	b = (h+w)/20;	/* Number of pixels of ignored border */
	for ( y=b; y<h-b; y++ ) {
		for ( x=b; x<w-b; x++ ) {
			uint16_t val;
			val = imagerecord.image[x+w*y];
			if ( val > max ) max = val;
			if ( val < min ) min = val;
		}
	}

	c = 0.1;
	scale = 255.0 / log(1+c*(max-min));

	/* Turn 16-bit image data into 8-bit display data */
	imagedisplay->data = malloc(3*w*h);
	for ( y=0; y<h; y++ ) {
		for ( x=0; x<w; x++ ) {

			uint16_t val16, val8;

			val16 = imagerecord.image[x+w*y];
			val8 = scale * log(1+c*(val16-min));

			imagedisplay->data[3*( x+w*(h-1-y) )] = val8;
			imagedisplay->data[3*( x+w*(h-1-y) )+1] = val8;
			imagedisplay->data[3*( x+w*(h-1-y) )+2] = val8;

		}
	}

	memcpy(&imagedisplay->imagerecord, &imagerecord, sizeof(ImageRecord));

	/* Create the pixbuf from the 8-bit display data */
	imagedisplay->pixbuf = gdk_pixbuf_new_from_data(imagedisplay->data,
				 GDK_COLORSPACE_RGB, FALSE, 8, w, h, w*3,
				 (GdkPixbufDestroyNotify)imagedisplay_free_data,
				 imagedisplay);

	if ( imagedisplay->realised ) {
		imagedisplay_force_redraw(imagedisplay);
	}
}

void imagedisplay_clear_marks(ImageDisplay *imagedisplay)
{
	ImageDisplayMark *cur;

	cur = imagedisplay->marks;
	while ( cur ) {
		ImageDisplayMark *next = cur->next;
		free(cur);
		cur = next;
	}
	imagedisplay->marks = NULL;
}

static void imagedisplay_destroyed(GtkWidget *widget,
				   ImageDisplay *imagedisplay)
{
	imagedisplay_clear_marks(imagedisplay);

	if ( imagedisplay->flags & IMAGEDISPLAY_QUIT_IF_CLOSED ) {
		gtk_exit(0);
	}

	g_object_unref(G_OBJECT(imagedisplay->gc_centre));
	g_object_unref(G_OBJECT(imagedisplay->gc_tiltaxis));
	g_object_unref(G_OBJECT(imagedisplay->gc_marks_1));
	g_object_unref(G_OBJECT(imagedisplay->gc_marks_2));

	if ( imagedisplay->flags & IMAGEDISPLAY_FREE ) {
		free(imagedisplay->imagerecord.image);
	}

	free(imagedisplay);
}

void imagedisplay_close(ImageDisplay *imagedisplay)
{
	imagedisplay->flags = (imagedisplay->flags
		| IMAGEDISPLAY_QUIT_IF_CLOSED)^IMAGEDISPLAY_QUIT_IF_CLOSED;
	if ( imagedisplay->window ) {
		gtk_widget_destroy(imagedisplay->window);
	}
}

static void imagedisplay_add_scalebar(ImageDisplay *imagedisplay,
				      GtkWidget *drawingarea, double scale,
				      double xoffs, double yoffs)
{
	PangoLayout *layout;
	double sb;
	PangoRectangle rect;
	int bwidth, bheight;
	int view_height = imagedisplay->view_height;

	sb = mapping_scale_bar_length(&imagedisplay->imagerecord);
	layout = gtk_widget_create_pango_layout(drawingarea, "1 nm^-1");
	pango_layout_get_pixel_extents(layout, &rect, NULL);

	bwidth = (sb*scale)+20;
	bheight = rect.height+30;
	if ( rect.width > bwidth ) bwidth = rect.width+20;
	gdk_draw_rectangle(drawingarea->window,
		drawingarea->style->bg_gc[GTK_WIDGET_STATE(drawingarea)],
		TRUE, xoffs+20, yoffs+view_height-20-bheight, bwidth, bheight);
	gdk_draw_line(drawingarea->window, imagedisplay->gc_scalebar,
				xoffs+30, yoffs+view_height-30,
				xoffs+30+(scale*sb), yoffs+view_height-30);
	gdk_draw_layout(drawingarea->window,
		drawingarea->style->fg_gc[GTK_WIDGET_STATE(drawingarea)],
		xoffs+30, yoffs+view_height-20-bheight+10, layout);
}

#define imagedisplay_draw_line(gc,x1,y1,x2,y2) \
		(gdk_draw_line(drawingarea->window,gc, \
		xoffs+(x1), yoffs+imagedisplay->view_height-1-(y1), \
		xoffs+(x2), yoffs+imagedisplay->view_height-1-(y2)))

static gboolean imagedisplay_redraw(GtkWidget *drawingarea,
				    GdkEventExpose *event,
				    ImageDisplay *imagedisplay)
{
	double scale, xoffs, yoffs;
	ImageDisplayMark *cur;
	double max;

	xoffs = ((double)imagedisplay->drawingarea_width
					- imagedisplay->view_width) / 2;
	yoffs = ((double)imagedisplay->drawingarea_height
					- imagedisplay->view_height) / 2;
	scale = (double)imagedisplay->view_width/imagedisplay->imagerecord.width;

	gdk_draw_pixbuf(drawingarea->window,
		drawingarea->style->bg_gc[GTK_WIDGET_STATE(drawingarea)],
		imagedisplay->pixbuf_scaled,
		0, 0, xoffs, yoffs, imagedisplay->view_width,
		imagedisplay->view_height, GDK_RGB_DITHER_NONE, 0, 0);

	if ( imagedisplay->flags & IMAGEDISPLAY_SHOW_TILT_AXIS ) {
		/* This is nasty, but works */
		imagedisplay_draw_line(imagedisplay->gc_tiltaxis,
			imagedisplay->imagerecord.x_centre * scale,
			imagedisplay->imagerecord.y_centre * scale,
			(imagedisplay->imagerecord.x_centre
			 + imagedisplay->imagerecord.width) * scale,
			(imagedisplay->imagerecord.y_centre
			 + imagedisplay->imagerecord.width
			 * tan(imagedisplay->imagerecord.omega)) * scale);
		imagedisplay_draw_line(imagedisplay->gc_tiltaxis,
			imagedisplay->imagerecord.x_centre * scale,
			imagedisplay->imagerecord.y_centre * scale,
			(imagedisplay->imagerecord.x_centre
			 - imagedisplay->imagerecord.width) * scale,
			(imagedisplay->imagerecord.y_centre
			 - imagedisplay->imagerecord.width
			 * tan(imagedisplay->imagerecord.omega)) * scale);
	}

	/* Add scale bar */
	if ( imagedisplay->flags & IMAGEDISPLAY_SCALE_BAR ) {
		imagedisplay_add_scalebar(imagedisplay, drawingarea, scale,
								xoffs, yoffs);
	}

	/* NB This calls the function above, which sorts out stuff */
	if ( imagedisplay->flags & IMAGEDISPLAY_SHOW_CENTRE ) {
		imagedisplay_draw_line(imagedisplay->gc_centre,
			imagedisplay->imagerecord.x_centre * scale - 10,
			imagedisplay->imagerecord.y_centre * scale,
			imagedisplay->imagerecord.x_centre * scale + 10,
			imagedisplay->imagerecord.y_centre * scale);
		imagedisplay_draw_line(imagedisplay->gc_centre,
			imagedisplay->imagerecord.x_centre * scale,
			imagedisplay->imagerecord.y_centre * scale - 10,
			imagedisplay->imagerecord.x_centre * scale,
			imagedisplay->imagerecord.y_centre * scale + 10);
	}

	/* Find the maximum intensity */
	cur = imagedisplay->marks;
	max = 0.0;
	while ( cur ) {

		if ( cur->weight < 0.0 ) {
			cur = cur->next;
			continue;
		}

		if ( log(1+0.1*cur->weight) > max )
						max = log(1+0.1*cur->weight);
		cur = cur->next;

	}

	cur = imagedisplay->marks;
	while ( cur ) {

		GdkGC *gc;

		switch ( cur->type ) {
			case IMAGEDISPLAY_MARK_CIRCLE_1 : {
				gc = imagedisplay->gc_marks_1;
				break;
			}
			case IMAGEDISPLAY_MARK_CIRCLE_2 : {
				gc = imagedisplay->gc_marks_2;
				break;
			}
			case IMAGEDISPLAY_MARK_CIRCLE_3 : {
				gc = imagedisplay->gc_marks_3;
				break;
			}
			case IMAGEDISPLAY_MARK_LINE_1 : {
				gc = imagedisplay->gc_marks_1;
				break;
			}
			case IMAGEDISPLAY_MARK_LINE_2 : {
				gc = imagedisplay->gc_marks_2;
				break;
			}
			default : gc = imagedisplay->gc_marks_1; break;
		}

		if ( (cur->type == IMAGEDISPLAY_MARK_CIRCLE_1)
		  || (cur->type == IMAGEDISPLAY_MARK_CIRCLE_2)
		  || (cur->type == IMAGEDISPLAY_MARK_CIRCLE_3) ) {

			double r;

			if ( cur->weight < 0.0 ) {
				cur = cur->next;
				continue;
			}

			if ( cur->type == IMAGEDISPLAY_MARK_CIRCLE_1 ) {
				r = 10.0;
			} else {
				r = 10.0 * (log(1+0.1*cur->weight)/max);
			}

			gdk_draw_arc(drawingarea->window, gc, FALSE,
			   xoffs + cur->x*scale - r,
			   yoffs + imagedisplay->view_height-1-cur->y*scale - r,
			   2*r, 2*r, 0, 64*360);

		} else if ( (cur->type == IMAGEDISPLAY_MARK_LINE_1)
			 || (cur->type == IMAGEDISPLAY_MARK_LINE_2) ) {

			gdk_draw_line(drawingarea->window, gc,
			     xoffs + cur->x*scale,
			     yoffs + imagedisplay->view_height-1-cur->y*scale,
			     xoffs + cur->x2*scale,
			     yoffs + imagedisplay->view_height-1-cur->y2*scale);

		}

		cur = cur->next;
	}

	return FALSE;

}

static gint imagedisplay_realize(GtkWidget *widget, ImageDisplay *imagedisplay)
{
	GdkColor colour;

	imagedisplay->gc_centre = gdk_gc_new(imagedisplay->drawingarea->window);
	gdk_color_parse("yellow", &colour);
	gdk_gc_set_rgb_fg_color(imagedisplay->gc_centre, &colour);

	imagedisplay->gc_tiltaxis = gdk_gc_new(imagedisplay->drawingarea->window);
	gdk_color_parse("#6600dd", &colour);
	gdk_gc_set_rgb_fg_color(imagedisplay->gc_tiltaxis, &colour);

	imagedisplay->gc_marks_1 = gdk_gc_new(imagedisplay->drawingarea->window);
	gdk_color_parse("#0077ff", &colour);
	gdk_gc_set_rgb_fg_color(imagedisplay->gc_marks_1, &colour);

	imagedisplay->gc_marks_2 = gdk_gc_new(imagedisplay->drawingarea->window);
	gdk_color_parse("#ffff00", &colour);
	gdk_gc_set_rgb_fg_color(imagedisplay->gc_marks_2, &colour);

	imagedisplay->gc_marks_3 = gdk_gc_new(imagedisplay->drawingarea->window);
	gdk_color_parse("#00ddff", &colour);
	gdk_gc_set_rgb_fg_color(imagedisplay->gc_marks_3, &colour);

	imagedisplay->gc_scalebar = gdk_gc_new(imagedisplay->drawingarea->window);
	gdk_color_parse("#000000", &colour);
	gdk_gc_set_rgb_fg_color(imagedisplay->gc_scalebar, &colour);
	gdk_gc_set_line_attributes(imagedisplay->gc_scalebar, 5,
				GDK_LINE_SOLID, GDK_CAP_BUTT, GDK_JOIN_MITER);

	imagedisplay->realised = TRUE;

	return 0;

}

ImageDisplay *imagedisplay_new_nowindow(ImageRecord imagerecord,
					ImageDisplayFlags flags,
					const char *message,
					GCallback mouse_click_func,
					gpointer callback_data)
{
	ImageDisplay *imagedisplay;

	imagedisplay = malloc(sizeof(ImageDisplay));
	imagedisplay->imagerecord = imagerecord;
	imagedisplay->view_width = 512;
	imagedisplay->view_height = 512;
	imagedisplay->message = message;
	imagedisplay->mouse_click_func = mouse_click_func;
	imagedisplay->flags = flags;
	imagedisplay->marks = NULL;
	imagedisplay->pixbuf = NULL;
	imagedisplay->pixbuf_scaled = NULL;
	imagedisplay->realised = FALSE;
	imagedisplay->window = NULL;

	imagedisplay_put_data(imagedisplay, imagerecord);

	imagedisplay->vbox = gtk_vbox_new(FALSE, 0);

	if ( message ) {
		GtkWidget *label;
		label = gtk_label_new(message);
		gtk_misc_set_alignment(GTK_MISC(label), 0, 0.5);
		gtk_box_pack_start(GTK_BOX(imagedisplay->vbox), label, FALSE,
								TRUE, 3);
	}

	imagedisplay->drawingarea = gtk_drawing_area_new();
	gtk_box_pack_start(GTK_BOX(imagedisplay->vbox),
				imagedisplay->drawingarea, TRUE, TRUE, 0);

	if ( imagedisplay->mouse_click_func ) {
		gtk_widget_add_events(GTK_WIDGET(imagedisplay->drawingarea),
							GDK_BUTTON_PRESS_MASK);
		g_signal_connect(GTK_OBJECT(imagedisplay->drawingarea),
				"button-press-event",
				G_CALLBACK(imagedisplay->mouse_click_func),
				callback_data);
	}

	g_signal_connect(GTK_OBJECT(imagedisplay->drawingarea),
				"realize",
				G_CALLBACK(imagedisplay_realize),
				imagedisplay);
	g_signal_connect(GTK_OBJECT(imagedisplay->drawingarea),
				"destroy",
				G_CALLBACK(imagedisplay_destroyed),
				imagedisplay);
	g_signal_connect(GTK_OBJECT(imagedisplay->drawingarea),
				"configure_event",
				G_CALLBACK(imagedisplay_configure_event),
				imagedisplay);
	g_signal_connect(GTK_OBJECT(imagedisplay->drawingarea),
				"expose-event",
				G_CALLBACK(imagedisplay_redraw), imagedisplay);

	return imagedisplay;

}

/* Display an image */
ImageDisplay *imagedisplay_open_with_message(ImageRecord imagerecord,
					     const char *title,
					     const char *message,
					     ImageDisplayFlags flags,
					     GCallback mouse_click_func,
					     gpointer callback_data)
{
	ImageDisplay *imagedisplay;
	GdkGeometry geom;

	imagedisplay = imagedisplay_new_nowindow(imagerecord, flags, message,
					mouse_click_func, callback_data);

	imagedisplay->window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
	gtk_container_add(GTK_CONTAINER(imagedisplay->window),
					imagedisplay->vbox);
	imagedisplay->title = strdup(title);
	gtk_window_set_title(GTK_WINDOW(imagedisplay->window),
					imagedisplay->title);

	geom.min_width = 128;	geom.min_height = 128;
	gtk_window_set_geometry_hints(GTK_WINDOW(imagedisplay->window),
					GTK_WIDGET(imagedisplay->drawingarea),
					&geom, GDK_HINT_MIN_SIZE);

	gtk_window_set_default_size(GTK_WINDOW(imagedisplay->window), 512, 512);

	gtk_widget_show_all(imagedisplay->window);

	return imagedisplay;
}

ImageDisplay *imagedisplay_open(ImageRecord image, const char *title,
				ImageDisplayFlags flags)
{
	return imagedisplay_open_with_message(image, title, NULL, flags,
								NULL, NULL);
}

void imagedisplay_add_mark(ImageDisplay *imagedisplay, double x, double y,
			   ImageDisplayMarkType type, double weight)
{
	ImageDisplayMark *new;

	new = malloc(sizeof(ImageDisplayMark));
	new->x = x;  new->y = y;
	new->type = type;
	new->weight = weight;
	new->next = NULL;

	if ( !imagedisplay->marks ) {
		imagedisplay->marks = new;
	} else {
		ImageDisplayMark *cur = imagedisplay->marks;
		while ( cur->next ) {
			cur = cur->next;
		}
		cur->next = new;
	}
}

void imagedisplay_add_line(ImageDisplay *imagedisplay, double x1, double y1,
			   double x2, double y2, ImageDisplayMarkType type)
{
	ImageDisplayMark *new;

	new = malloc(sizeof(ImageDisplayMark));
	new->x = x1;  new->y = y1;
	new->x2 = x2;  new->y2 = y2;
	new->type = type;
	new->weight = 1.0;	/* This field makes little sense for a line */
	new->next = NULL;

	if ( !imagedisplay->marks ) {
		imagedisplay->marks = new;
	} else {
		ImageDisplayMark *cur = imagedisplay->marks;
		while ( cur->next ) {
			cur = cur->next;
		}
		cur->next = new;
	}
}

void imagedisplay_force_redraw(ImageDisplay *imagedisplay)
{
	imagedisplay_rescale(imagedisplay, imagedisplay->drawingarea_width,
					imagedisplay->drawingarea_height);
	gtk_widget_queue_draw_area(imagedisplay->drawingarea, 0, 0,
					imagedisplay->drawingarea_width,
					imagedisplay->drawingarea_height);
}