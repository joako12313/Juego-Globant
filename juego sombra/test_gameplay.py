"""Pruebas de regresion para fisica y puzzles principales de SHADOW."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import main


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.game = main.Game()
        self.game.start_level(0)

    def place_actor(self, x, y, vx=0.0, vy=0.0):
        self.game.x = float(x)
        self.game.y = float(y)
        self.game.actor.topleft = (x, y)
        self.game.vx = vx
        self.game.vy = vy
        self.game.grounded = False

    def test_swept_collisions_stop_walls_floor_and_ceiling(self):
        self.game.platforms = [pygame.Rect(130, 500, 20, 100)]
        self.place_actor(80, 520, vx=2000)
        self.game.resolve_actor(False, 0.1)
        self.assertEqual(self.game.actor.right, 130)

        self.game.platforms = [pygame.Rect(0, 620, 300, 100)]
        self.place_actor(100, 400, vy=2200)
        self.game.resolve_actor(False, 0.1)
        self.assertEqual(self.game.actor.bottom, 620)
        self.assertTrue(self.game.grounded)

        self.game.platforms = [pygame.Rect(0, 200, 300, 20)]
        self.place_actor(100, 300, vy=-2200)
        self.game.resolve_actor(False, 0.1)
        self.assertEqual(self.game.actor.top, 220)
        self.assertEqual(self.game.vy, 0)

    def test_player_lands_stably_and_can_jump_again(self):
        for _ in range(120):
            self.game.update(1 / 60, False)
        self.assertTrue(self.game.grounded)
        self.assertEqual(self.game.actor.bottom, 620)

        self.game.update(1 / 60, True)
        self.assertLess(self.game.vy, 0)
        self.assertLess(self.game.actor.y, 570)
        for _ in range(90):
            self.game.update(1 / 60, False)
        self.assertTrue(self.game.grounded)
        self.assertEqual(self.game.actor.bottom, 620)

    def test_echo_history_samples_exact_three_second_offset(self):
        history = main.EchoHistory(main.SHADOW_DELAY)
        history.reset(main.EchoFrame(0.0, 0, 0, 0, 0, 1, True, "idle"))
        history.record(main.EchoFrame(4.0, 400, 80, 100, 0, 1, True, "walk"))
        sample = history.sample(4.5 - main.SHADOW_DELAY)
        self.assertEqual(sample.time, 1.5)
        self.assertEqual(sample.x, 150)

    def test_echo_is_required_to_reach_first_levels_cornice(self):
        floor = self.game.platforms[0]
        cornice = self.game.platforms[3]
        echo_x = cornice.x - 110
        echo_top = floor.top - main.PLAYER_SIZE[1] - 2
        self.game.sim_time = main.SHADOW_DELAY
        self.game.echo_rect = pygame.Rect(echo_x, echo_top, *main.PLAYER_SIZE)
        self.game.previous_echo_rect = self.game.echo_rect.copy()
        self.place_actor(echo_x - 20, floor.top - main.PLAYER_SIZE[1])
        self.game.grounded = True

        def jump_until_landed(move_right):
            self.game.vx = 0.0
            self.game.vy = -main.JUMP_SPEED
            self.game.grounded = False
            for _ in range(90):
                self.game.vy = min(main.MAX_FALL_SPEED, self.game.vy + main.GRAVITY / 60)
                self.game.vx = (min(main.PLAYER_SPEED, self.game.vx + main.PLAYER_ACCEL / 60)
                                if move_right else 0.0)
                self.game.resolve_actor(True, 1 / 60)
                if self.game.grounded:
                    return True
            return False

        self.assertTrue(jump_until_landed(False))
        self.assertEqual(self.game.actor.bottom, self.game.echo_rect.top)
        self.assertTrue(jump_until_landed(True))
        self.assertEqual(self.game.actor.bottom, cornice.top)
        self.assertTrue(self.game.grounded)

        self.game.start_level(0)
        self.place_actor(echo_x - 20, floor.top - main.PLAYER_SIZE[1])
        self.game.vy = -main.JUMP_SPEED
        for _ in range(90):
            self.game.vy = min(main.MAX_FALL_SPEED, self.game.vy + main.GRAVITY / 60)
            self.game.vx = min(main.PLAYER_SPEED, self.game.vx + main.PLAYER_ACCEL / 60)
            self.game.resolve_actor(True, 1 / 60)
            if self.game.grounded:
                break
        self.assertGreater(self.game.actor.bottom, cornice.top)

    def test_moving_platform_carries_rider_while_rising(self):
        self.game.start_level(1)
        platform = self.game.moving[0]
        self.place_actor(platform.rect.x + 50, platform.rect.top - main.PLAYER_SIZE[1])
        self.game.grounded = True
        start_x = self.game.actor.x
        for _ in range(90):
            self.game.update(1 / 60, False)
        self.assertTrue(self.game.grounded)
        self.assertEqual(self.game.actor.bottom, platform.rect.top)
        self.assertNotEqual(self.game.actor.x, start_x)

    def test_level_two_lift_is_boardable_when_it_returns_to_shore(self):
        held_keys = set()
        original_get_pressed = pygame.key.get_pressed
        self.addCleanup(setattr, pygame.key, "get_pressed", original_get_pressed)
        pygame.key.get_pressed = lambda: type(
            "KeyState", (), {"__getitem__": lambda _, key: key in held_keys}
        )()
        self.game.start_level(1)

        def tick(right=False, jump=False):
            held_keys.clear()
            if right:
                held_keys.add(pygame.K_d)
            self.game.update(1 / 60, jump)

        while self.game.actor.x < 350:
            tick(right=True)
        for _ in range(300):
            if self.game.moving[0].rect.x <= 440:
                break
            tick()
        self.assertLessEqual(self.game.moving[0].rect.x, 440)
        tick(right=True, jump=True)
        for _ in range(90):
            tick(right=True)
            if self.game.grounded and self.game.actor.bottom == self.game.moving[0].rect.top:
                break
        self.assertTrue(self.game.grounded)
        self.assertEqual(self.game.actor.bottom, self.game.moving[0].rect.top)

    def test_echo_platform_carries_player_horizontally(self):
        self.game.platforms = []
        self.game.history.reset(main.EchoFrame(0.0, 200, 500, 0, 0, 1, True, "idle"))
        self.game.history.record(main.EchoFrame(1.0, 300, 500, 100, 0, 1, True, "walk"))
        self.game.echo_rect = pygame.Rect(200, 500, *main.PLAYER_SIZE)
        self.game.previous_echo_rect = self.game.echo_rect.copy()
        self.game.sim_time = main.SHADOW_DELAY
        self.place_actor(200, 450)
        self.game.grounded = True
        self.game.update(1 / 60, False)
        self.assertTrue(self.game.grounded)
        self.assertEqual(self.game.actor.bottom, self.game.echo_rect.top)
        self.assertEqual(self.game.actor.x - 200, self.game.echo_rect.x - 200)

    def test_closed_door_blocks_player_until_echo_opens_it(self):
        door = self.game.doors["gate"]
        self.place_actor(door.left - 100, 570, vx=2000)
        self.game.resolve_actor(False, 0.1)
        self.assertEqual(self.game.actor.right, door.left)

        switch = self.game.mechanisms[0]
        self.game.sim_time = main.SHADOW_DELAY
        self.game.echo_rect = switch.rect.copy()
        self.game.update_mechanisms()
        self.place_actor(door.left - 100, 570, vx=2000)
        self.game.resolve_actor(False, 0.1)
        self.assertGreater(self.game.actor.x, door.right)

    def test_shadow_switch_latches_door_open(self):
        switch = self.game.mechanisms[0]
        self.game.sim_time = main.SHADOW_DELAY
        self.game.echo_rect = switch.rect.copy()
        self.game.update_mechanisms()
        self.assertTrue(self.game.door_open[switch.target])
        self.game.echo_rect = pygame.Rect(-100, -100, *main.PLAYER_SIZE)
        self.game.update_mechanisms()
        self.game.echo_rect = switch.rect.copy()
        self.game.update_mechanisms()
        self.assertTrue(self.game.door_open[switch.target])

    def test_echo_switch_materializes_required_bridge(self):
        self.game.start_level(1)
        bridge = self.game.platform_groups["bridge_west"][0]
        self.assertNotIn(bridge, self.game.actor_solids())
        switch = next(item for item in self.game.mechanisms if item.target == "bridge_west")
        self.game.sim_time = main.SHADOW_DELAY
        self.game.echo_rect = switch.rect.copy()
        self.game.update_mechanisms()
        self.assertTrue(self.game.platform_group_active["bridge_west"])
        self.assertIn(bridge, self.game.actor_solids())

    def test_every_gap_wider_than_jump_range_has_a_bridge_or_lift(self):
        maximum_jump_range = main.PLAYER_SPEED * (2 * main.JUMP_SPEED / main.GRAVITY)
        for level in main.LEVELS:
            floor_intervals = sorted((x, x + width) for x, y, width, height in level["platforms"]
                                     if y == 620 and height >= 90)
            moving_intervals = [(min(platform[1][0], platform[2][0]),
                                 max(platform[1][0], platform[2][0]) + platform[0][2])
                                for platform in level["moving"]]
            bridge_intervals = [(x, x + width) for group in level["platform_groups"].values()
                                for x, _, width, _ in group]
            for (_, left_end), (right_start, _) in zip(floor_intervals, floor_intervals[1:]):
                gap = right_start - left_end
                if gap <= maximum_jump_range:
                    continue
                covered = any(start <= left_end + 25 and end >= right_start - 25
                              for start, end in moving_intervals + bridge_intervals)
                self.assertTrue(covered, f"{level['title']} has an uncovered {gap}px pit")

    def test_final_echo_switch_materializes_last_bridge(self):
        self.game.start_level(2)
        bridge = self.game.platform_groups["bridge_gamma"][0]
        switch = next(item for item in self.game.mechanisms if item.target == "bridge_gamma")
        self.assertNotIn(bridge, self.game.actor_solids())
        self.game.sim_time = main.SHADOW_DELAY
        self.game.echo_rect = switch.rect.copy()
        self.game.update_mechanisms()
        self.assertIn(bridge, self.game.actor_solids())

    def test_final_upper_route_requires_echo_and_opens_its_gate(self):
        def attempt_with_echo(use_echo):
            game = main.Game()
            game.start_level(2)
            game.platform_group_active["bridge_beta"] = True
            game.sim_time = main.SHADOW_DELAY if use_echo else 0.0
            game.echo_rect = pygame.Rect(2890, 495, *main.PLAYER_SIZE)
            game.previous_echo_rect = game.echo_rect.copy()
            game.x, game.y = 2890.0, 495.0
            game.actor.topleft = (2890, 495)
            game.grounded = True

            def jump(move_right):
                game.vx = 0.0
                game.vy = -main.JUMP_SPEED
                game.grounded = False
                for _ in range(90):
                    game.vy = min(main.MAX_FALL_SPEED, game.vy + main.GRAVITY / 60)
                    game.vx = (min(main.PLAYER_SPEED, game.vx + main.PLAYER_ACCEL / 60)
                               if move_right else 0.0)
                    game.resolve_actor(use_echo, 1 / 60)
                    if game.grounded:
                        return

            if use_echo:
                jump(False)
                self.assertTrue(game.grounded)
                self.assertEqual(game.actor.bottom, game.echo_rect.top)
            jump(True)
            return game

        echo_route = attempt_with_echo(True)
        direct_route = attempt_with_echo(False)
        final_shelf = next(platform for platform in echo_route.platforms if platform.top == 475)
        self.assertEqual(echo_route.actor.bottom, final_shelf.top)
        self.assertNotEqual(direct_route.actor.bottom, final_shelf.top)

        final_switch = next(item for item in echo_route.mechanisms if item.target == "final_seal")
        echo_route.sim_time = main.SHADOW_DELAY
        echo_route.echo_rect = final_switch.rect.copy()
        echo_route.update_mechanisms()
        self.assertTrue(echo_route.door_open["final_seal"])

    def test_level_one_temporal_route_reaches_exit(self):
        held_keys = set()
        original_get_pressed = pygame.key.get_pressed
        self.addCleanup(setattr, pygame.key, "get_pressed", original_get_pressed)
        pygame.key.get_pressed = lambda: type(
            "KeyState", (), {"__getitem__": lambda _, key: key in held_keys}
        )()
        self.game.start_level(0)

        def tick(right=False, jump=False):
            held_keys.clear()
            if right:
                held_keys.add(pygame.K_d)
            self.game.update(1 / 60, jump)

        def walk_to(x, limit=700):
            for _ in range(limit):
                if self.game.actor.x >= x or self.game.state != "PLAYING":
                    break
                tick(right=True)
            self.assertTrue(self.game.actor.x >= x or self.game.state == "LEVEL_COMPLETE")

        walk_to(390)
        tick(right=True, jump=True)
        walk_to(650)
        walk_to(770)
        for _ in range(190):
            tick()
        tick(jump=True)
        for _ in range(55):
            tick()
        self.assertEqual(self.game.actor.bottom, self.game.echo_rect.top)

        cornice = self.game.platforms[3]
        tick(right=True, jump=True)
        for _ in range(60):
            tick(right=True)
            if self.game.grounded and self.game.actor.bottom == cornice.top:
                break
        self.assertTrue(self.game.grounded)
        self.assertEqual(self.game.actor.bottom, cornice.top)

        walk_to(1220)
        first_shelf, second_shelf = self.game.platforms[4:6]
        self.assertEqual(self.game.actor.bottom, first_shelf.top)
        tick(right=True, jump=True)
        for _ in range(60):
            tick(right=True)
            if self.game.grounded and self.game.actor.bottom == second_shelf.top:
                break
        self.assertEqual(self.game.actor.bottom, second_shelf.top)

        walk_to(1750)
        for _ in range(200):
            tick()
        self.assertTrue(self.game.door_open["gate"])
        tick(right=True, jump=True)
        walk_to(2040)
        self.assertGreaterEqual(self.game.active_checkpoint, 0)

        walk_to(2626)
        for _ in range(200):
            tick()
        self.assertTrue(self.game.door_open["seal"])
        walk_to(2830)
        self.assertEqual(self.game.state, "LEVEL_COMPLETE")

    def test_hazard_respawn_keeps_checkpoint_and_restarts_echo_there(self):
        self.game.start_level(1)
        self.game.active_checkpoint = 1
        checkpoint = self.game.checkpoints[1]
        hazard = self.game.hazards[0]
        self.game.x, self.game.y = float(hazard.x + 20), float(hazard.y)
        self.game.actor.topleft = (round(self.game.x), round(self.game.y))
        self.game.vx = self.game.vy = 0.0
        self.game.update(1 / 60, False)
        self.assertEqual(self.game.active_checkpoint, 1)
        self.assertEqual(self.game.actor.topleft, checkpoint)
        self.assertEqual(self.game.history.frames[0].x, checkpoint[0])

    def test_echo_uses_same_animated_silhouette_as_player(self):
        rect = pygame.Rect(12, 7, *main.PLAYER_SIZE)
        for action in ("idle", "walk", "jump", "fall"):
            frame = main.EchoFrame(3.0, 0, 0, 0, 0, -1, False, action, 0.73)
            self.game.animation = frame.action
            self.game.animation_time = frame.animation_time
            self.game.facing = frame.facing
            player_surface = pygame.Surface((64, 64), pygame.SRCALPHA)
            echo_surface = pygame.Surface((64, 64), pygame.SRCALPHA)
            self.game.draw_player(player_surface, rect)
            self.game.draw_player(echo_surface, rect, True, frame, 205)
            player_mask = pygame.mask.from_surface(player_surface, 1)
            echo_mask = pygame.mask.from_surface(echo_surface, 1)
            self.assertEqual(player_mask.count(), echo_mask.count(), action)
            self.assertEqual(player_mask.overlap_area(echo_mask, (0, 0)), player_mask.count(), action)


if __name__ == "__main__":
    unittest.main()